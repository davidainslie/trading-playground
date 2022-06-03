from dataclasses import dataclass

@dataclass(frozen = True)
class TickerStatements:
    ticker: str
    balanceSheet: {}
    incomeStatement: {}
    cashStatement: {}
