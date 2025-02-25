# SamsungScraper

SamsungScraper is an asynchronous web scraper designed to extract product details from the Samsung website using Playwright and BeautifulSoup. It enables automated searches for product specifications, dimensions, and certifications while handling missing data efficiently.

## Features
- **Asynchronous Web Scraping**: Utilizes Playwright for fast and efficient data extraction.
- **Product Search**: Automatically retrieves the first search result URL based on a given search term.
- **Data Extraction**: Extracts product specifications, dimensions, certifications, and other key details.
- **Rich Output**: Uses `rich` for better console output formatting.
- **Excel Integration**: Reads input data from an Excel file and stores extracted results in a structured format.

## Installation

Ensure you have Python 3.8+ installed, then install the required dependencies:

```sh
pip install asyncio pandas playwright rich beautifulsoup4 fractions openpyxl
playwright install
```

## Usage

1. Prepare an Excel file containing product search terms in the `Grainger` sheet.
2. Run the scraper by initializing an instance of `SamsungScraper` and calling its methods.

### Example

```python
import asyncio
from samsung_scraper import SamsungScraper

async def main():
    scraper = SamsungScraper(
        excel_path="input.xlsx",
        output_filename="output.xlsx",
        baseurl="https://www.samsung.com/search/",
        found=0,
        missing=0,
        headless=True
    )
    await scraper.launch_browser()
    product_url = await scraper.search_product("Samsung TV")
    if product_url:
        product_data = await scraper.scrape_product_details(product_url)
        print(product_data)
    await scraper.close_browser()

asyncio.run(main())
```

## Methods

- `launch_browser()`: Initializes and launches the Playwright browser.
- `close_browser()`: Closes the browser and Playwright instance.
- `search_product(search_term: str)`: Searches for a product and returns its first result URL.
- `scrape_product_details(url: str)`: Extracts details from a given product URL.
- `extract_dimensions(data: dict)`: Parses and extracts product dimensions from specification data.
- `check_certification(data: dict)`: Determines whether a product has certifications.

## Notes
- Ensure that Playwright is properly installed using `playwright install` before running the scraper.
- Some products may not have complete specifications, so the scraper is designed to handle missing values gracefully.

## License
This project is licensed under the MIT License.

## Author
#### Developed by VEGLO H. Gabin





