# FINMARKET Kart Essentials

**FINMARKET Kart Essentials** is a multi-category online shopping platform designed to bring groceries, food products, household essentials, fashion, electronics, sports products, mobile gadgets and healthcare essentials together in one convenient shopping destination.

The platform uses the FINMARKET brand identity and is designed to support a scalable product catalogue, category-based browsing, product search, pagination, customer accounts, shopping carts and order management.

---

## 1. Project Overview

FINMARKET Kart Essentials is designed as a multi-category e-commerce application with the following objectives:

- Provide a convenient online shopping experience.
- Organize products into 16 active shopping categories.
- Support up to 300 products per selected category in the configured catalogue-fetch workflow.
- Provide category-based product browsing.
- Support product search, filtering and pagination.
- Maintain unique product SKUs.
- Display product images, descriptions, prices and pack sizes.
- Support customer shopping and order workflows.
- Provide an expandable catalogue for future product additions.

### Important Catalogue Capacity Update

The product retrieval limit has been updated to support:

| Setting | Updated value |
| --- | ---: |
| Maximum products per selected category | 300 |
| Total fetch capacity | 300 products |

The application can retrieve up to 300 products belonging to a selected category, subject to the API response and available database records.

This is a retrieval capacity, not a claim that every category already contains 300 products.

---

## 2. FINMARKET Kart Essentials – 16 Categories

The application currently uses the following 16 active top-level categories.

| ID | Category Name | Category Slug | Description |
| ---: | --- | --- | --- |
| 1 | Fruits & Vegetables | `fruits-vegetables` | Fresh fruits and farm-fresh vegetables. |
| 2 | Dairy & Eggs | `dairy-eggs` | Milk, dairy products and fresh eggs. |
| 3 | Bakery | `bakery` | Fresh bread, biscuits and bakery essentials. |
| 4 | Rice & Grains | `rice-grains` | Everyday rice, grains and cereals. |
| 5 | Pulses & Lentils | `pulses-lentils` | Protein-rich pulses, beans and lentils. |
| 6 | Snacks & Munchies | `snacks` | Chips, namkeen and everyday snacks. |
| 7 | Beverages | `beverages` | Juices, tea, coffee and refreshing drinks. |
| 8 | Cooking Essentials | `cooking-essentials` | Oils, spices, salt and cooking ingredients. |
| 9 | Personal Care | `personal-care` | Daily hygiene and personal care essentials. |
| 10 | Household Essentials | `household` | Cleaning and everyday household supplies. |
| 11 | Mobile Gadgets | `mobile-gadgets` | Smartphones, smart devices and mobile gadgets. |
| 12 | Accessories | `accessories` | Mobile accessories, headphones, chargers and other useful accessories. |
| 13 | Electronics | `electronics` | Televisions, mixie grinders and electronic home appliances. |
| 14 | Sports | `sports` | Sports equipment, fitness products and outdoor games. |
| 15 | Clothes & Fashion | `clothes-fashion` | Clothing, fashion wear, footwear, shoes, sandals, slippers, ethnic wear, western wear, men's fashion, women's fashion, kids' clothing, innerwear, accessories, winter wear, blankets and other wearable and textile essentials for the whole family. |
| 16 | Medicines & Healthcare | `medicines-healthcare` | Medicines and healthcare essentials, including prescription medicines, over-the-counter medicines, pain relief, cold and cough remedies, fever care, digestive health products, first aid supplies, antiseptics, wound care and medical devices. |

All category IDs, names and slugs should match the deployed database.

---

## 3. Category Catalogue Development

Each category is designed to support a large and expandable product catalogue.

The catalogue should contain genuine individual products with accurate product information.

### Catalogue requirements

- Unique product SKU.
- Product name.
- Product slug.
- Short description.
- Full description.
- Correct category ID.
- Brand information where available.
- Selling price in INR.
- Compare-at price where applicable.
- Product unit.
- Pack size or weight where available.
- Product image URL.
- Product image alt text.
- Published status.
- Featured status.

### Product image requirements

Product images should:

- Match the actual product.
- Match the listed pack size wherever possible.
- Use direct image-file URLs.
- Be clear and suitable for storefront display.
- Come from official brands, manufacturers or reliable retailers.
- Avoid placeholder, dummy or unrelated image URLs.

If an appropriate image cannot be verified, do not invent an image URL.

---

## 4. Catalogue Progress and Product SKU Structure

The following are the current catalogue targets and SKU ranges.

| Category | Target Products | SKU Range |
| --- | ---: | --- |
| Fruits & Vegetables | Expandable | Category-specific |
| Dairy & Eggs | 200 | `DE-001` – `DE-200` |
| Bakery | Expandable | Category-specific |
| Rice & Grains | Expandable | Category-specific |
| Pulses & Lentils | Expandable | Category-specific |
| Snacks & Munchies | 300 | `SN-001` – `SN-300` |
| Beverages | Expandable | Category-specific |
| Cooking Essentials | Expandable | Category-specific |
| Personal Care | Expandable | Category-specific |
| Household Essentials | 180 | `HE-001` – `HE-180` |
| Mobile Gadgets | Expandable | Category-specific |
| Accessories | Expandable | Category-specific |
| Electronics | Expandable | Category-specific |
| Sports | Expandable | Category-specific |
| Clothes & Fashion | 300 | `CF-001` – `CF-300` |
| Medicines & Healthcare | Expandable | Category-specific |

**Note:** These figures represent catalogue targets or previously assembled SKU ranges. Confirm actual product counts, imports and publication status against the live database.

## Snacks & Munchies – 300 Products

Target SKU range:

`SN-001` through `SN-300`

The catalogue covers:

- Potato chips.
- Corn snacks.
- Extruded snacks.
- Traditional Indian namkeen.
- Andhra traditional snacks.
- Murukulu and janthikalu.
- Chekkalu and chekodilu.
- Boondi and mixtures.
- Popcorn.
- Roasted and healthy snacks.
- Biscuits and cookies.
- Crackers.
- Chocolates.
- Toffees and candies.
- Coffee candies.
- Chocolate wafers.
- Traditional Indian sweets.
- Regional sweets.
- Karachi Bakery products.
- Parle Krack Jack biscuits.

The missing SKU `SN-292` was assigned to:

### Assigned replacement product

The final catalogue should contain 300 unique SKU codes without missing sequence numbers.

## Clothes & Fashion – 300 Products

Target SKU range:

`CF-001` through `CF-300`

The catalogue covers:

- Men's clothing.
- Women's clothing.
- Kids' clothing.
- Men's T-shirts.
- Women's T-shirts.
- Shirts.
- Jeans and trousers.
- Formal clothing.
- Casual clothing.
- Ethnic wear.
- Western wear.
- Innerwear.
- Women's bras and innerwear.
- Men's vests and innerwear.
- Maternity and nursing bras.
- Camisoles and slips.
- Shapewear.
- Period underwear.
- Thermal innerwear.
- Footwear.
- Shoes.
- Sandals and slippers.
- Winter wear.
- Blankets and textile essentials.
- Fashion accessories.

Required brands include OTTO, Ramraj and Uthayam, alongside other relevant brands.

## Dairy & Eggs – 200 Products

Target SKU range:

`DE-001` through `DE-200`

The catalogue includes:

- Milk.
- Curd.
- Yogurt.
- Buttermilk.
- Paneer.
- Butter.
- Ghee.
- Cheese.
- Cream.
- Flavoured milk.
- Milkshakes.
- Dairy desserts.
- Fresh eggs.
- Other relevant dairy products.

Required brand coverage includes Heritage, Amul, Jersey, Dodla, Hatsun and other relevant dairy brands.

## Household Essentials – 180 Products

Target SKU range:

`HE-001` through `HE-180`

The catalogue covers:

- Pooja essentials.
- Kitchen and dining.
- Cookware.
- Utensils.
- Storage products.
- Kitchen appliances.
- Bedroom essentials.
- Living room products.
- Furniture.
- Bedding.
- Lighting.
- Safety products.
- Tools.
- Work and study stationery.
- Outdoor and balcony essentials.
- Other household accessories.

---

## 5. Application Architecture

The project includes the following application components.

| Component | Responsibility |
| --- | --- |
| Angular Client | Storefront interface and customer-facing pages |
| FastAPI Backend | REST API and application services |
| MySQL Database | Persistent product, category and commerce data |
| Streamlit Application | Python-based application interface |
| Alembic | Database migration management |
| SQL Scripts | Database creation, catalogue and publishing operations |
| Git | Source control and project version management |

### General architecture

```text
                 FINMARKET Kart Essentials
                           |
              +------------+------------+
              |                         |
         Angular Client             Streamlit App
              |                         |
              +------------+------------+
                           |
                       FastAPI
                           |
              +------------+------------+
              |                         |
        Catalogue API              Commerce API
              |                         |
              +------------+------------+
                           |
                       MySQL
                           |
              +------------+------------+
              |                         |
           Categories               Products
              |                         |
              +------------+------------+
                           |
                    Orders and Cart
                    
