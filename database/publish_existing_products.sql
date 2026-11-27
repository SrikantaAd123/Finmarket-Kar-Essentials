-- FINMARKET Kart Essentials: publish existing active, non-deleted products.
-- Review before execution. This does not insert/delete products or recreate tables.
-- Uses the existing products.image_url column and existing local frontend image assets.

USE `Finmarket_Kart_Essentials`;

START TRANSACTION;

UPDATE products AS p
LEFT JOIN categories AS c ON c.id = p.category_id
SET
    p.is_published = 1,
    p.image_url = COALESCE(
        NULLIF(TRIM(p.image_url), ''),
        CASE
            WHEN LOWER(p.name) LIKE '%apple%' OR LOWER(p.name) LIKE '%orange%' THEN '/static/images/products/apple.jpg'
            WHEN LOWER(p.name) LIKE '%banana%' THEN '/static/images/products/banana.jpg'
            WHEN LOWER(p.name) LIKE '%tomato%' THEN '/static/images/products/tomato.jpg'
            WHEN LOWER(p.name) LIKE '%potato%' OR LOWER(p.name) LIKE '%chips%' THEN '/static/images/products/potato.jpg'
            WHEN LOWER(p.name) LIKE '%onion%' THEN '/static/images/products/onion.jpg'
            WHEN LOWER(p.name) LIKE '%carrot%' THEN '/static/images/products/carrot.jpg'
            WHEN LOWER(p.name) LIKE '%spinach%' OR LOWER(p.name) LIKE '%broccoli%' OR LOWER(p.name) LIKE '%capsicum%' OR LOWER(p.name) LIKE '%cauliflower%' THEN '/static/images/products/spinach.jpg'
            WHEN LOWER(p.name) LIKE '%milk%' OR LOWER(p.name) LIKE '%paneer%' OR LOWER(p.name) LIKE '%curd%' OR LOWER(p.name) LIKE '%yogurt%' THEN '/static/images/products/milk.jpg'
            WHEN LOWER(p.name) LIKE '%butter%' OR LOWER(p.name) LIKE '%cheese%' THEN '/static/images/products/butter.jpg'
            WHEN LOWER(p.name) LIKE '%egg%' THEN '/static/images/products/eggs.jpg'
            WHEN LOWER(p.name) LIKE '%bread%' OR LOWER(p.name) LIKE '%bun%' OR LOWER(p.name) LIKE '%cookie%' OR LOWER(p.name) LIKE '%biscuit%' OR LOWER(p.name) LIKE '%cake%' OR LOWER(p.name) LIKE '%rusk%' THEN '/static/images/products/bread.jpg'
            WHEN LOWER(p.name) LIKE '%rice%' OR LOWER(p.name) LIKE '%poha%' OR LOWER(p.name) LIKE '%oat%' OR LOWER(p.name) LIKE '%flour%' OR LOWER(p.name) LIKE '%ragi%' THEN '/static/images/products/rice.jpg'
            WHEN LOWER(p.name) LIKE '%moong%' THEN '/static/images/products/moong-dal.jpg'
            WHEN LOWER(p.name) LIKE '%dal%' OR LOWER(p.name) LIKE '%lentil%' OR LOWER(p.name) LIKE '%chana%' OR LOWER(p.name) LIKE '%rajma%' OR LOWER(p.name) LIKE '%urad%' OR LOWER(p.name) LIKE '%masoor%' THEN '/static/images/products/toor-dal.jpg'
            WHEN LOWER(p.name) LIKE '%oil%' THEN '/static/images/products/cooking-oil.jpg'
            WHEN LOWER(p.name) LIKE '%sugar%' OR LOWER(p.name) LIKE '%salt%' OR LOWER(p.name) LIKE '%turmeric%' OR LOWER(p.name) LIKE '%chilli%' OR LOWER(p.name) LIKE '%masala%' OR LOWER(p.name) LIKE '%coriander%' THEN '/static/images/products/sugar.jpg'
            WHEN LOWER(p.name) LIKE '%tea%' OR LOWER(p.name) LIKE '%coffee%' OR LOWER(p.name) LIKE '%juice%' OR LOWER(p.name) LIKE '%drink%' THEN '/static/images/products/tea.jpg'
            WHEN LOWER(c.name) LIKE '%personal%' THEN '/static/images/categories/beauty-personal-care.jpg'
            WHEN LOWER(c.name) LIKE '%household%' THEN '/static/images/categories/home-kitchen-living.jpg'
            WHEN LOWER(c.name) LIKE '%beverage%' OR LOWER(c.name) LIKE '%snack%' THEN '/static/images/banners/snacks-beverages.jpg'
            WHEN LOWER(c.name) LIKE '%fruit%' OR LOWER(c.name) LIKE '%vegetable%' THEN '/static/images/banners/fruits-vegetables.jpg'
            WHEN LOWER(c.name) LIKE '%dairy%' OR LOWER(c.name) LIKE '%egg%' THEN '/static/images/products/milk.jpg'
            WHEN LOWER(c.name) LIKE '%bakery%' THEN '/static/images/products/bread.jpg'
            WHEN LOWER(c.name) LIKE '%rice%' OR LOWER(c.name) LIKE '%grain%' THEN '/static/images/products/rice.jpg'
            WHEN LOWER(c.name) LIKE '%pulse%' OR LOWER(c.name) LIKE '%lentil%' THEN '/static/images/products/toor-dal.jpg'
            WHEN LOWER(c.name) LIKE '%cooking%' THEN '/static/images/products/cooking-oil.jpg'
            ELSE '/static/images/logo/finmarket-kart-essentials-icon.png'
        END
    ),
    p.updated_at = CURRENT_TIMESTAMP
WHERE p.is_active = 1
  AND p.is_deleted = 0;

COMMIT;

-- Confirm published catalogue totals.
SELECT
    COUNT(*) AS total_products,
    SUM(is_active = 1) AS active_products,
    SUM(is_published = 1) AS published_products,
    SUM(is_deleted = 0) AS non_deleted_products,
    SUM(image_url IS NOT NULL AND TRIM(image_url) <> '') AS products_with_image_urls
FROM products;

-- Inspect a sample of records after the update.
SELECT id, sku, name, price, stock_quantity, is_active, is_published, is_deleted, image_url
FROM products
WHERE is_active = 1 AND is_deleted = 0
ORDER BY id
LIMIT 20;
