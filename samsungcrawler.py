import asyncio
import pandas as pd
from playwright.async_api import async_playwright, expect
from rich import print
import re
from bs4 import BeautifulSoup

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
        url_to_navigate = self.baseurl + str(search_term).replace(('"'), "in").replace(',', "").replace("(", "").replace(")", "").replace(" ", "%20")
        # print(url_to_navigate)
        try:
            await self.page.goto(url_to_navigate)
            await expect(self.page.locator('div.TabHeader-module__tabHeader___3VfJw')).to_be_visible(timeout=15000)
            # Get the first product URL
            search_result = await self.page.locator('//a[@class="ProductCard__learnmore___2ICzV"]').all()
            if search_result:
                url = await search_result[0].get_attribute('href')
                url = "https://www.samsung.com" + url.replace("/#benefits", "")
                return url
        except Exception as e:
            # print(f"Error occurred: {e}")
            pass
        return None

    async def scrape_product_details(self, url: str):
        """Extract product details from the given URL."""
        print(f"[cyan]Scraping data from:[/cyan] {url}")
        new_page = await self.context.new_page()
        await new_page.goto(url)
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
            "dimensions": {},
            "standard features": []
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
                # spec_groups_ul = soup.find("ul", class_="Specs_specRow__e9Ife Specs_specDetailList__StjuR")
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

                
        

            print(specifications)
        except Exception as e:
            print(f"Error extracting image: {e}")
            

        # Extract Product Image (jpg)
        try:
            
            image_locators =soup.find_all("img")
            if image_locators:
                # data["image"] = await image_locator.get("href")
                # print("Product Image : ", image_locator.get("href"))
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
            print(data["description"])
        except Exception as e:
            print(f"Error extracting description: {e}")

        # Extract Measurements and Dimensions
        try:
            pass
            # Locate each row in the dimensions table
            # dimension_rows = await new_page.locator('//div[@id="collapsemanualOne"]//table//tr').all()
            # for row in dimension_rows:
            #     cells = await row.locator('td').all_text_contents()
            #     if len(cells) >= 2:
            #         label = cells[0].strip()
            #         value = cells[1].strip()
            #         if "Overall Width" in label:
            #             data["dimensions"]["width"] = value.split('"')[0]
            #         if "Overall Height" in label:
            #             data["dimensions"]["height"] = value.split('"')[0]
            #         if "Weight Capacity" in label:
            #             data["dimensions"]["weight"] = value.split('lbs')[0]
            #         if "Overall Depth" in label:
            #             data["dimensions"]["depth"] = value.split('"')[0]                     
            #         data["dimensions"][label] = value

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
                    print(price)
                else:
                    print("Price not found inside <b> tag.")
            else:
                price_span = soup.find("span", class_ = "product-top-nav__font-price")
                if price_span:
                    price = price_span.get_text(strip=True)
                    data["price"] = price
                    print(price)
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
                print(spec_pdf)
            else:
                print("Specification pdf download not found")
        except Exception as e:
            print(f"Error extracting spec_pdf: {e}")

        await new_page.close()
        return data


    async def run(self):
        """Main function to scrape product details and save them to an Excel file."""
        await self.launch_browser()
        await self.page.goto(self.baseurl)
    
        for index, row in self.df.iterrows():
            mfr_number = row["mfr number"]
            model_name = row['model name']
            url = await self.search_product(str(mfr_number).replace("/", "%2F"))

            if not url:
                
                url = await self.search_product(str(model_name).replace(" ", "%20"))
                # if url:
                    # print(f"{mfr_number} | {model_name}")
            if not url:
                self.missing += 1
            else:
                self.found += 1
            # print(url)

            # print(url)
        # print(I)

            if url:
                product_data = await self.scrape_product_details(url)
        #         if product_data:
        #             print(f"[green]{model_name} | {mfr_number} [/green] - Data extracted successfully.")
        #             self.df.at[index, "Product URL"] = product_data.get("url", "")
        #             self.df.at[index, "Product Image (jpg)"] = product_data.get("image", "")
        #             self.df.at[index, "Product Image"] = product_data.get("image", "")
        #             self.df.at[index, "product description"] = product_data.get("description", "")
        #             self.df.at[index, "depth"] = product_data["dimensions"].get("depth", "")
        #             self.df.at[index, "height"] = product_data["dimensions"].get("height", "")
        #             self.df.at[index, "width"] = product_data["dimensions"].get("width", "")
        #             self.df.at[index, "weight"] = product_data["dimensions"].get("weight", "")
        #             self.df.at[index, "green certification? (Y/N)"] = "N"
        #             self.df.at[index, "emergency_power Required (Y/N)"] = "N"
        #             self.df.at[index, "dedicated_circuit Required (Y/N)"] = "N"
        #             self.df.at[index, "water_cold Required (Y/N)"] = "N"
        #             self.df.at[index, "water_hot  Required (Y/N)"] = "N"
        #             self.df.at[index, "drain Required (Y/N)"] = "N"
        #             self.df.at[index, "water_treated (Y/N)"] = "N"
        #             self.df.at[index, "steam  Required(Y/N)"] = "N"
        #             self.df.at[index, "vent  Required (Y/N)"] = "N"
        #             self.df.at[index, "vacuum Required (Y/N)"] = "N"
        #             self.df.at[index, "ada compliant (Y/N)"] = "N"
        #             self.df.at[index, "antimicrobial coating (Y/N)"] = "N"
        #     else:
        #         print(f"[red]{model_name} | {mfr_number} [/red] - Not found")
        # print(f"[red]Missing : {self.missing} [/red]")
        # print(f"[green]Found : {self.found} [/green]")
        # self.df.to_excel(self.output_filename, index=False, sheet_name="Grainger")
        # await self.close_browser()


if __name__ == "__main__":
    scraper = SamsungScraper(
        excel_path="Samsung Content.xlsx",
        output_filename="output/Samsung-output.xlsx",
        baseurl = "https://www.samsung.com/us/search/searchMain/?listType=g&searchTerm=",
        found = 0 ,
        missing = 0,
        headless=False
    )
    asyncio.run(scraper.run())