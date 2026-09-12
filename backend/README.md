# Ingest Folders (local & S3)

1.  Manually Download data on PC, whence it is converted to json and uploaded to S3
    -   a.  ETrade Account .csv exports
    -   b.  ETrade Market data (Morningstar, Morgan Stanley) PDFs converted to structured json
    -   c.  ingest triggered by S3 ObjectCreate

2.  Market data retrieved via API calls
    -   a.  Scheduled Lambda retrieves Danefin scores for specified symbols to json docs
    -   b.  yahoo finance quotes and tickers
    -   b.  ingest triggered by S3 ObjectCreate

3.  news and information uploaded to ./news 
    -   a.  Manually downloaded news articles PDFs S3
    -   b.  Emails forwarded via SES converted from .eml to .md (eml_to_markdown.py)
    -   c.  S3 ObjectCreate triggers AI researcher to process and store in S3 vector database


./ingest
-   **/accounts** -- downloads from E*Trade (IBKR) contain account & positions info
-   **/market_data** -- danelfin, ETrade PDFs (Morningstar, Morgan Stanley) converted to structured json, ETrade Screener-Exports
-   **/news** -- web articles saved as PDFs, email newsletters (*.eml converted to Markdown )

An S3 ObjectCreated event on each of these folders processes file contents and moves the source file into a date subfolder **/YYYY-MM-DD

A local utility syncs the local folder with S3 on demand (may eventually implement windows scheduler)
