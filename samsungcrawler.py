import asyncio
import pandas as pd
from playwright.async_api import async_playwright, expect
from rich import print
import re
from fractions import Fraction
from bs4 import BeautifulSoup
import os
from urllib.parse import quote_plus


class SamsungScraper:
    """Web scraper for extracting product details from the Champion Manufacturing."""
    def __init__(self, excel_path: str, output_filename: str, baseurl : str, found : int, missing : int, headless: bool = False):
        self.filepath = excel_path
        self.output_filename = output_filename
        self.baseurl = baseurl
        self.headless = headless
        self.found = found
        self.missing = missing
        self.df = pd.read_excel(self.filepath, sheet_name="Grainger")
        self.mfr_number = ""

    async def launch_browser(self):
        """Initialize Playwright and open the browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def close_browser(self):
        """Close the browser and Playwright instance."""
        await self.browser.close()
        await self.playwright.stop()

    async def search_product(self, search_term: str):
        """Search for a product by search term  and return its first result URL."""
        # Properly encode the search term for use in a URL
        formatted_search_term = quote_plus(search_term)
        print((search_term, formatted_search_term))
        url_to_navigate = self.baseurl + formatted_search_term
        try:
            await self.page.goto(url_to_navigate, timeout=0)
            await expect(self.page.locator('div.TabHeader-module__tabHeader___3VfJw')).to_be_visible(timeout=5000)
            search_results = await self.page.locator("div.ProductCard__container___3tGUh").all()
            if search_results:
                if len(search_results)==9:
                    while True:
                        await self.page.wait_for_timeout(30000)
                        view_more_button = self.page.locator('div[data-link_id="view more"]').first
                        if await view_more_button.is_visible():
                            print("Found 'View more' button. Clicking...")
                            await view_more_button.click()
                            if not await view_more_button.is_visible(timeout=10000):
                                print("No more 'View more' button found. Exiting loop.")
                                break
                        else:
                            print("'View more' button not visible. Exiting loop.")
                            break
                search_results = await self.page.locator("div.ProductCard__container___3tGUh").all()
                print(f"Found {len(search_results)} products")

                for product in search_results:
                    mdl_code = await product.get_attribute("data-mdlcode")
                    if mdl_code.lower() in self.mfr_number.lower():
                        first_a_tag = product.locator("a").first
                        url = "https://www.samsung.com" + await first_a_tag.get_attribute("href")

                        print(f"Model Code: {mdl_code}, Link: {url}")
                        return url
                    else:
                        pass
                return None
                
        except Exception as e:
            # print(f"Error occurred: {e}")
            pass
        return None

    def extract_dimensions(self, data):
        dimensions = {"width": None, "height": None, "depth": None, "weight": None, "shipping_weight": None}

        def extract_number(value):
            """Extracts the first numeric value from a string."""
            match = re.findall(r"[\d.]+", value)
            return match[0] if match else None

        def extract_dimensions_from_string(value):
            """Extracts width, height, and depth from a formatted dimension string (e.g., '22.9" D x 32.0" H x 23.7" W')."""
            match = re.findall(r"([\d.]+)[\"']?\s*[D|d]?\s*[xX]\s*([\d.]+)[\"']?\s*[H|h]?\s*[xX]\s*([\d.]+)[\"']?\s*[W|w]?", value)
            if match:
                return match[0]  
            else:
                match = extract_dimensions_from_string_fraction(value)
                return match
            return None
        
        def extract_dimensions_from_string_fraction(value):
            """Extracts width, height, and depth from a formatted dimension string (e.g., '30" W x 5 1/10" H x 21 1/4" D')."""
            
            def convert_to_decimal(fraction_str):
                """Converts a fraction string (e.g., '1/10') to a decimal number."""
                try:
                    return float(Fraction(fraction_str))
                except ValueError:
                    return None
            
            # Pattern to match dimensions like '30" W x 5 1/10" H x 21 1/4" D'
            match = re.findall(r"([\d\s/]+)[\"']?\s*[W|w]?\s*[xX]\s*([\d\s/]+)[\"']?\s*[H|h]?\s*[xX]\s*([\d\s/]+)[\"']?\s*[D|d]?", value)
            
            if match:
                width = match[0][0]
                height = match[0][1]
                depth = match[0][2]

                # Convert fraction dimensions to decimal
                width_decimal = convert_to_decimal(width.replace(" ", "").replace('"', ''))
                height_decimal = convert_to_decimal(height.replace(" ", "").replace('"', ''))
                depth_decimal = convert_to_decimal(depth.replace(" ", "").replace('"', ''))

                return (width_decimal, height_decimal, depth_decimal)
            
            return None
        
        dimension_keys = [
            "Set Dimension without Stand (WxHxD)",
            "Set Without Stand",
            "Product Size (W x H x D) Without Stand?Width, height and depth of the television, without stand, as measured in inches (in.).",
            "Dimensions (WxHxD)",
            "Set Dimension (WxHxD)",
            "Box Dimension (inches, WxHxD)",
            "Product Size (W x H x D) Without Stand",
            "Dimension (WxHxD)",
            "Product Dimensions without Hinges or Handles",
            "Product Dimensions",
            "Product Dimensions Without Stand",
            "Main Unit Size (Inch)"
        ]
        weight_keys = [
            "Weight",
            "Set Weight without Stand",
            "Set Without Stand",
            "Product Weight Without Stand?Weight of the television, without stand, as measured in pounds (lb.).",
            "Weight (lbs)",
            "Product Weight",
            "Package Weight",
            "Product Weight Without Stand",
            "Product Weight (lbs.)"
        ]
        shipping_weight_keys = [
            "Shipping Weight?Weight of the television, with shipping container, as measured in pounds (lbs.).",
            "Shipping Weight (lbs.)",
            "Shipping Weight"
        ]
        voltz = ""
        hertz = ""
        amps = ""
        watts = ""

        for section, attributes in data.items():
            if isinstance(attributes, dict):
                for key, value in attributes.items():
                    if isinstance(value, str):
                        if any(dim_key.lower() == key.lower() for dim_key in dimension_keys):
                            dim_match = extract_dimensions_from_string(value)
                            if dim_match:
                                dimensions["width"], dimensions["height"], dimensions["depth"] = dim_match
                        if any(weight_key.lower() == key.lower() for weight_key in weight_keys):
                                dimensions["weight"] = extract_number(value)
                        if any(shipping_key.lower() == key.lower() for shipping_key in shipping_weight_keys):
                            dimensions["shipping_weight"] = extract_number(value)

                    if "Voltz/Hertz/Amps" in key:
                        voltz, hertz, amps = map(str.strip, value.split("/"))
                    elif "Watts" in key:
                        watts = value.strip()
                    elif "Voltz" in key and all(x not in key for x in ["Hertz", "Amps"]):
                        voltz = value.strip()
                    elif "Hertz" in key and all(x not in key for x in ["Voltz", "Amps"]):
                        hertz = value.strip()
                    elif "Amps" in key and all(x not in key for x in ["Voltz", "Hertz"]):
                        amps = value.strip()

        return dimensions, [voltz, hertz, amps, watts]
    

    def check_certification(self, data):
        # Convert all the values in the dictionary to lowercase
        def recursive_lower(d):
            if isinstance(d, dict):
                return {k: recursive_lower(v) for k, v in d.items()}
            elif isinstance(d, str):
                return d.lower()
            return d
        
        data_lower = recursive_lower(data)
        
        def contains_certification(d):
            if isinstance(d, dict):
                for value in d.values():
                    if contains_certification(value):
                        return True
            elif isinstance(d, str):
                if 'certification' in d or 'certifications' in d:
                    return True
            return False
        
        # Return 'Y' if 'certification' or 'certifications' is found, otherwise 'N'
        if contains_certification(data_lower):
            return "Y"
        else:
            return "N"
      
    async def scrape_product_details(self, url: str):
        """Extract product details from the given URL."""
        print(f"[cyan]Scraping data from:[/cyan] {url}")
        new_page = await self.context.new_page()
        await new_page.goto(url, timeout = 0)
        expand_btn = new_page.locator('//a[(normalize-space(text())="See All Specs") or (@aria-label="See All Specs")]').first
        await expand_btn.wait_for(state="visible", timeout=15000)  # Wait until visible
        await expect(expand_btn).to_be_visible(timeout=15000)
        await expand_btn.click(force=True)
        await new_page.wait_for_timeout(1000)
        data = {
            "url": url,
            "image": "",
            "price" : "",
            "description": "",
            "specifications": {},
            "dimensions" : "",
            "green_certification" : "",
            "spec_pdf" : ""
        }

        specifications = {}

        #Extract Specificatiobns
        try:
            html_content = await new_page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            spec_groups_ul = soup.find("ul", class_ = "row spec-details__list")
            if spec_groups_ul:
                spec_li = spec_groups_ul.find_all("li", itemscope=True)
            
                for section in spec_li:
                    category_name_elem = section.find('span', itemprop='name')

                    # Check if the category name exists
                    if category_name_elem:
                        category = category_name_elem.text.strip()
                        specifications[category] = {}

                        # Find all spec items within the section
                        spec_items = section.find_all('div', class_='sub-specs__item')
                        
                        for item in spec_items:
                            # Extract key and value from each spec item
                            key_elem = item.find('span', class_='specs-item-name')
                            value_elem = item.find('p', class_='sub-specs__item__value')
                            
                            if key_elem and value_elem:
                                key = key_elem.text.strip()
                                value = value_elem.text.strip()
                                specifications[category][key] = value
                            else:
                                print(f"Missing key/value in item: {item}")
                    else:
                        print("Category name missing for section:", section)
            else:
                spec_groups_ul = soup.find("ul", class_ = "Specs_specRow__e9Ife Specs_specDetailList__StjuR")
                if spec_groups_ul:
                    spec_li = spec_groups_ul.find_all("li")

                    for section in spec_li:
                        category_name_elem = section.find('figcaption')
                        
                        # Check if the category name exists
                        if category_name_elem:
                            category = category_name_elem.text.strip()
                            specifications[category] = {}

                            # Find all spec items within the section
                            spec_items = section.find_all('div', class_='subSpecsItem')

                            for item in spec_items:
                                # Extract key and value from each spec item
                                key_elem = item.find('div', class_='Specs_subSpecItemName__IUPV4')
                                value_elem = item.find('div', class_='Specs_subSpecsItemValue__oWnMq')

                                if key_elem and value_elem:
                                    key = key_elem.text.strip()
                                    value = value_elem.text.strip()
                                    specifications[category][key] = value
                                else:
                                    print(f"Missing key/value in item: {item}")
                        else:
                            print("Category name missing for section:", section)
                else:
                    print("Specification groups not found.")

            data["specifications"] = specifications
            # print(specifications)
        except Exception as e:
            print(f"Error extracting image: {e}")
            
        # Extract Product Image (jpg)
        try:
            
            image_locators =soup.find_all("img")
            if image_locators:
                for item in image_locators:
                    src = item.get("src")
                    if src and src.startswith("https://image-us.samsung.com") and ".png" not in src:
                        data["image"] = src.replace("$", "")
                        print(src.replace("$", ""))
                        break
            else:
                print("Product Image Not  found ")
        except Exception as e:
            print(f"Error extracting image: {e}")

        # Extract Product Description
        try:
        
            description_locator = soup.find("ul", class_ = "product-details__info-description")
            if description_locator:
                data["description"] = description_locator.get_text().replace("\n", "").replace("\t", "")
            else:
                description_locator = soup.find("div", class_ = "ProductSummary_detailList__zDn4_" )
                if description_locator:
                    data["description"] = description_locator.get_text().replace("\n", "").replace("\t", "")
            # print(data["description"])
        except Exception as e:
            print(f"Error extracting description: {e}")

        # Extract Measurements and Dimensions
        try:
            dimensions, voltz_hertz_amps_watts = self.extract_dimensions(data["specifications"])
            data["dimensions"] = dimensions
            data['volts'] , data["hertz"], data["amps"], data["watts"] = voltz_hertz_amps_watts
            print(voltz_hertz_amps_watts)
        except Exception as e:
            print(f"Error extracting dimensions: {e}")

        # Extract Price
        try:
            price_div = soup.find("div", class_="PriceInfoText_priceInfo__QEjy8")
            if price_div:
                price_tag = price_div.find("b")  # Find the bold price text
                if price_tag:
                    price = price_tag.text.strip()
                    data["price"] = price
                    # print(price)
                else:
                    print("Price not found inside <b> tag.")
            else:
                price_span = soup.find("span", class_ = "product-top-nav__font-price")
                if price_span:
                    price = price_span.get_text(strip=True)
                    data["price"] = price
                    # print(price)
                else:
                    print("Price div not found.")
        except Exception as e:
            print(f"Error extracting price: {e}")

        #Extract Specification pdf download link
        try:
            spec_pdf_div = soup.find('div', class_ = "span-sm-2 span-lg-2 spec-download")
            if spec_pdf_div:
                spec_pdf = spec_pdf_div.find("a").get("href")
                data["spec_pdf"] = spec_pdf
                # print(spec_pdf)

        except Exception as e:
            print(f"Error extracting spec_pdf: {e}")

        #Extract green certification
        try:
            data["green_certification"]  = self.check_certification(specifications)
                
        except Exception as e:
            print(f"Error extracting certification: {e}")
        await new_page.close()
        return data


    async def run(self):
        """Main function to scrape product details and save them to an Excel file."""
        await self.launch_browser()
        await self.page.goto(self.baseurl, timeout = 0)
    
        for index, row in self.df.iterrows():
            mfr_number = row["mfr number"]
            self.mfr_number = str(mfr_number)
            model_name = row['model name']
            url = await self.search_product(str(mfr_number))

            if not url:
                url = await self.search_product(str(model_name))
            if not url:
                self.missing += 1
            else:
                self.found += 1
            if url:
                product_data = await self.scrape_product_details(url)
                if product_data:
                    print(f"[green]{model_name} | {mfr_number} [/green] - Data extracted successfully.")
                    self.df.at[index, "Product URL"] = product_data.get("url", "")
                    self.df.at[index, "Product Image (jpg)"] = product_data.get("image", "")
                    self.df.at[index, "Product Image"] = product_data.get("image", "")
                    self.df.at[index, "product description"] = product_data.get("description", "")
                    self.df.at[index, "Specification Sheet (pdf)"] = product_data.get("spec_pdf", "")
                    self.df.at[index, "unit cost"] = product_data.get("price", "")
                    self.df.at[index, "depth"] = product_data["dimensions"].get("depth", "")
                    self.df.at[index, "height"] = product_data["dimensions"].get("height", "")
                    self.df.at[index, "width"] = product_data["dimensions"].get("width", "")
                    self.df.at[index, "weight"] = product_data["dimensions"].get("weight", "")
                    self.df.at[index, "ship_weight"] = product_data["dimensions"].get("shipping_weight", "")
                    self.df.at[index, "green certification? (Y/N)"] = product_data.get("green_certification", "")
                    self.df.at[index, "volts"] = product_data.get("volts", "")
                    self.df.at[index, "hertz"] = product_data.get("hertz", "")
                    self.df.at[index, "amps"] = product_data.get("amps", "")
                    self.df.at[index, "watts"] = product_data.get("watts", "")
                    self.df.at[index, "emergency_power Required (Y/N)"] = "N"
                    self.df.at[index, "dedicated_circuit Required (Y/N)"] = "N"
                    self.df.at[index, "water_cold Required (Y/N)"] = "N"
                    self.df.at[index, "water_hot  Required (Y/N)"] = "N"
                    self.df.at[index, "drain Required (Y/N)"] = "N"
                    self.df.at[index, "water_treated (Y/N)"] = "N"
                    self.df.at[index, "steam  Required(Y/N)"] = "N"
                    self.df.at[index, "vent  Required (Y/N)"] = "N"
                    self.df.at[index, "vacuum Required (Y/N)"] = "N"
                    self.df.at[index, "ada compliant (Y/N)"] = "N"
                    self.df.at[index, "antimicrobial coating (Y/N)"] = "N"
            else:
                print(f"[red]{model_name} | {mfr_number} [/red] - Not found")
        print(f"[red]Missing : {self.missing} [/red]")
        print(f"[green]Found : {self.found} [/green]")
        self.df.to_excel(self.output_filename, index=False, sheet_name="Grainger")
        await self.close_browser()

if __name__ == "__main__":
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    scraper = SamsungScraper(
        excel_path="Samsung Content.xlsx",
        output_filename="output/Samsung-output.xlsx",
        baseurl = "https://www.samsung.com/us/search/searchMain/?listType=g&searchTerm=",
        found = 0 ,
        missing = 0,
        headless=False
    )
    asyncio.run(scraper.run())