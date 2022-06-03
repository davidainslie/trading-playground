import datetime as dt
import os
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Union, Any, List
import pandas as pd
import concurrent.futures as cf
from bs4.element import PageElement
from requests import Response
from yahoofinancials import YahooFinancials
import pprint
import re
import ast
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, ParseResult
from functools import partial
from functions import apply
import ray
from tickerstatements import TickerStatements
import json

asx200Url: ParseResult = urlparse("https://www.asx200list.com")
allOrdsUrl: ParseResult = urlparse("https://www.allordslist.com")
smallOrdsUrl: ParseResult = urlparse("https://www.smallordslist.com")

header: Dict[str, str] = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}

response: Response = requests.get(asx200Url.geturl(), headers = header)
soup: BeautifulSoup = BeautifulSoup(response.content, "html.parser")
table: Union[PageElement, Any] = soup.findAll("table", class_ = "tableizer-table sortable")[0]

def tickers(url: ParseResult) -> List[str]:
  response = requests.get(url.geturl(), headers = header)
  soup = BeautifulSoup(response.content, "html.parser")
  table = soup.findAll("table", class_ = "tableizer-table sortable")[0]

  return [row.findAll("td")[0].text.strip() for row in table.tbody.findAll("tr")]

asx200Tickers: List[str] = list(map(lambda s: s + ".AX", tickers(asx200Url)))

def tickerStatements(ticker: str) -> TickerStatements:
    print(f"Acquiring statements for {ticker}")
    yahooFinancials = YahooFinancials(ticker)
    annualStatements = partial(yahooFinancials.get_financial_stmts, "annual")

    balanceSheet, incomeStatement, cashStatement =\
      ray.get([apply.remote(f) for f in [
        lambda: annualStatements("balance")["balanceSheetHistory"][ticker],
        lambda: annualStatements("income")["incomeStatementHistory"][ticker],
        lambda: annualStatements("cash")["cashflowStatementHistory"][ticker]
      ]])

    return TickerStatements(
      ticker,
      balanceSheet,
      incomeStatement,
      cashStatement
    )

def persist(tickerStatements: List[TickerStatements], directory: str):
  if not os.path.exists(directory):
    os.makedirs(directory)

  # TODO - Save on 3 parallel threads
  with open(f"./{directory}/balance-sheets.json", "w") as output:
    json.dump(dict([(ts.ticker, ts.balanceSheet) for ts in tickerStatements]), output, indent = 2)

  with open(f"./{directory}/income-statements.json", "w") as output:
    json.dump(dict([(ts.ticker, ts.incomeStatement) for ts in tickerStatements]), output, indent = 2)

start = time.time()
executor: ThreadPoolExecutor = cf.ThreadPoolExecutor(16)
#asx200TickerStatements: list[Future[TickerStatements]] = [executor.submit(tickerStatements, ticker) for ticker in asx200Tickers]
asx200TickerStatementsFutures: list[Future[TickerStatements]] = [executor.submit(tickerStatements, ticker) for ticker in [asx200Tickers[0], asx200Tickers[2], asx200Tickers[3]]]

asx200TickerStatements: list[TickerStatements] = [future.result() for future in asx200TickerStatementsFutures]
pprint.pprint(asx200TickerStatements)

end = time.time()
print('  time taken {:.2f} s'.format(end - start))

# Persist statements
persist(asx200TickerStatements, "statements/asx200")

# To read back in
with open(f"./statements/asx200/balance-sheets.json", "r") as input:
  balanceSheets: dict = json.load(input)

pprint.pprint(balanceSheets)

with open(f"./statements/asx200/income-statements.json", "r") as input:
  incomeStatements: dict = json.load(input)

pprint.pprint(incomeStatements)


# return on equity (ROE) = net income / shareholder's equity

# earnings per share (EPS) = profit / common shares

# earnings per share growth (EPSG) = % annualised increase in EPS

# TODO - Sort out this copy and paste from some geeza
roe_dict, epsg_dict = {}, {}

count_missing, count_cond, count_eps_0 = 0, 0, 0

for (keyB, valB), (keyI, valI) in zip(balanceSheets.items(), incomeStatements.items()):
  try:
    if keyB == keyI:
      yearsI = [k for year in valI for k, v in year.items()]
      yearsB = [k for year in valB for k, v in year.items()]
      if yearsI == yearsB:
        count_cond += 1
        equity = [v['totalStockholderEquity'] for year in valB for k, v in year.items()]
        commonStock = [v['commonStock'] for year in valB for k, v in year.items()]

        profit = [v['grossProfit'] for year in valI for k, v in year.items()]
        revenue = [v['totalRevenue'] for year in valI for k, v in year.items()]
        netIncome = [v['netIncome'] for year in valI for k, v in year.items()]

        roe = [round(netin / equity * 100, 2) for netin, equity in zip(netIncome, equity)]
        roe_dict[keyB] = (round(sum(roe) / len(roe), 2), roe)

        eps = [round(earn / stono, 2) for earn, stono in zip(profit, commonStock)]

        try:
          epsg = []
          for ep in range(len(eps)):
            if ep == 0:
              continue
            elif ep == 1:
              epsg.append(round(100 * ((eps[ep - 1] / eps[ep]) - 1), 2))
            elif ep == 2:
              epsg.append(round(100 * ((eps[ep - 2] / eps[ep]) ** (1 / 2) - 1), 2))
              epsg.append(round(100 * ((eps[ep - 1] / eps[ep]) - 1), 2))
            elif ep == 3:
              epsg.append(round(100 * ((eps[ep - 3] / eps[ep]) ** (1 / 3) - 1), 2))
              epsg.append(round(100 * ((eps[ep - 1] / eps[ep]) - 1), 2))
            else:
              print('More than 4 years of FY data')

          epsg_dict[keyB] = (round(sum(epsg) / len(epsg), 2), epsg)
        except:
          count_eps_0 += 1
          epsg_dict[keyB] = (0, eps)

  except:
    count_missing += 1

print(f"Yearly data avail {count_cond} out of {len(balanceSheets)}")
print(f"Some key data missing {count_missing} out of {len(balanceSheets)}")
print(f"EPS Growth NaN {count_eps_0} out of {len(balanceSheets)}")