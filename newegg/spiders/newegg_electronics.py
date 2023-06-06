import scrapy
from scrapy.http import Response

class NeweggElectronicsSpider(scrapy.Spider):
    name = "newegg_electronics"
    allowed_domains = ["www.newegg.com"]
    start_urls = ["https://www.newegg.com/Electronics/Store/ID-10"]
    categories_xpath = "//*[@class='filter-box is-active is-category']/dd/ul/li/div/a/text()"
    categories_links_xpath = "//*[@class='filter-box is-active is-category']/dd/ul/li/div/a/@href"
    subcategories_xpath = "//*[@class='filter-box is-active is-category']/dd/ul/li/a/text()"
    subcategories_links_xpath = "//*[@class='filter-box is-active is-category']/dd/ul/li/a/@href"
    items_xpath = "//*[@class='item-info']/a/@href"

    def get_item_list_links(
            self, response: Response, xpath: str, links_xpath: str
        ):
        categories_list = response.xpath(xpath).extract()
        categories_link_list = response.xpath(links_xpath).extract()
        return categories_list, categories_link_list

    def parse(self, response: Response):
        categories_list, categories_link_list = self.get_item_list_links(
            response, 
            self.categories_xpath, 
            self.categories_links_xpath
        )
        for name, link in zip(categories_list, categories_link_list):
            yield response.follow(
                response.urljoin(link), 
                callback=self.DFS, 
            )
        
    def DFS(self, response: Response):
        """
        This function simulates the Depth First Search visiting all the\n
        categories and sub categories until it finds the product listing page.
        """
        categories_list, categories_link_list = self.get_item_list_links(
            response,
            self.subcategories_xpath,
            self.subcategories_links_xpath
        )
        category_tree = response.meta.get('category_tree')
        if len(categories_list) > 0 and len(categories_link_list) > 0:
            # This condition is true if selected page has some more categories available.
            for name, link in zip(categories_list, categories_link_list):
                yield response.follow(
                    response.urljoin(link), 
                    callback=self.DFS, 
                )
        else:
            # Shows that this is the product listing page so items must be fetched.
            items_urls = response.xpath(self.items_xpath)
            for url, item_count in zip(items_urls.extract(), range(5)):
                # Range function ristrict only 5 products perpage to prevent IP ban.
                yield response.follow(
                    response.urljoin(url),
                    callback=self.extract_product_info,
                )

    def extract_product_info(self, response: Response):
        product_name = response.xpath("//*[@class='product-title']/text()").get()
        category_tree = response.xpath("//*[@class='breadcrumb']/li/a/text()").extract()
        status = response.xpath("//*[@class='product-inventory']/strong/text()").get()
        product_price_dollars = response.xpath("//*[@class='price-current']/strong/text()").get()
        product_price_cents = response.xpath("//*[@class='price-current']/sup/text()").get()
        warranty = response.xpath("(//*[@class='info-item'])[1]/ul/li/text()").extract()
        item = {
            "Item Link": response.url,
            "Item Name": product_name,
            "Manufacturer": category_tree[-1],
            "Model": "n/a",
            "Price Currency": "USD",
            "Item Category": category_tree[1],
            "Item Category Tree": "/".join(category_tree),
            "Availability": status,
            "OEM Warranty": "\n".join(warranty),
        }
        if product_price_dollars and product_price_cents:
            item["Item Price"] = product_price_dollars + product_price_cents
        else:
            item["Item Price"] = "n/a"

        yield item  
