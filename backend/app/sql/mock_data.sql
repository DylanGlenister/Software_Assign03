# Active: 1747886189739@@127.0.0.1@3306@awe_electronics
-- Mock Data for Updated Database Schema
-- This script assumes the tables have been created as per the provided schema.

-- -----------------------------------------------------
-- Table `Tag`
-- `name` VARCHAR(50)
-- -----------------------------------------------------
INSERT INTO `Tag` (`name`) VALUES
('Electronics'),
('Books & Literature'),
('Home & Kitchen Appliances'),
('Fashion & Apparel'),
('Sports & Outdoors Equipment'),
('PC Gaming Peripherals'),
('Sustainable Products'),
('Travel Essentials');

-- -----------------------------------------------------
-- Table `Image`
-- `url` VARCHAR(255)
-- -----------------------------------------------------
INSERT INTO `Image` (`url`) VALUES
('https://picsum.photos/id/10/800/600'), -- Laptop
('https://picsum.photos/id/20/800/600'), -- Mouse
('https://picsum.photos/id/30/800/600'), -- Book
('https://picsum.photos/id/40/800/600'), -- Coffee Maker
('https://picsum.photos/id/50/800/600'), -- Running Shoes
('https://picsum.photos/id/60/800/600'), -- Tent
('https://picsum.photos/id/70/800/600'), -- Keyboard
('https://picsum.photos/id/80/800/600'), -- Knife Set
('https://picsum.photos/id/11/800/600'), -- Laptop Alt View
('https://picsum.photos/id/41/800/600'); -- Coffee Maker Lifestyle

-- -----------------------------------------------------
-- Table `Product`
-- `name` VARCHAR(100), `description` TEXT
-- -----------------------------------------------------
INSERT INTO `Product` (`name`, `description`, `price`, `stock`, `available`, `creationDate`, `discontinued`) VALUES
('UltraSlim Laptop Pro 15.6"', 'Experience top-tier performance with the UltraSlim Laptop Pro. Features a stunning 15.6" 4K display, Intel Core i9 processor, 32GB DDR5 RAM, and a 1TB NVMe SSD. Perfect for professionals and creatives. Includes a backlit keyboard and Thunderbolt 4 ports.', 1899.99, 75, 70, '2024-01-10 10:00:00', 0),
('Precision Wireless Ergonomic Mouse', 'Designed for comfort and precision, this wireless mouse features an ergonomic vertical design to reduce wrist strain. With 6 programmable buttons, adjustable DPI up to 4000, and a long-lasting rechargeable battery, it is ideal for extended work sessions.', 69.99, 250, 240, '2024-01-15 11:00:00', 0),
('The Future of Code: AI in Development', 'A groundbreaking book exploring the transformative impact of artificial intelligence on software development. Covers machine learning models for code generation, automated testing, and AI-driven project management. Essential reading for developers and tech leaders.', 49.95, 300, 290, '2024-02-01 09:30:00', 0),
('Smart Bean-to-Cup Coffee Maker', 'Wake up to perfectly brewed coffee with this smart coffee maker. Features a built-in grinder, programmable brew strength and temperature, and Wi-Fi connectivity for control via a mobile app. Brews up to 12 cups and includes a thermal carafe.', 199.50, 120, 115, '2024-02-20 14:00:00', 0),
('TrailBlazer Men\'s Running Shoes', 'Conquer any trail with the TrailBlazer running shoes. Engineered for durability and comfort, they feature a breathable mesh upper, responsive cushioning, and a high-traction rubber outsole for superior grip on varied terrain. Available in multiple colors.', 135.00, 180, 170, '2024-03-05 16:00:00', 0),
('AllWeather Family Camping Tent - 6 Person', 'This spacious 6-person tent is perfect for family adventures. Made from durable, waterproof ripstop polyester with taped seams. Features easy setup, multiple windows for ventilation, and an extended vestibule for gear storage. Includes a carrying bag.', 249.99, 90, 85, '2024-03-10 10:20:00', 0),
('StealthStrike RGB Mechanical Gaming Keyboard', 'Dominate the competition with the StealthStrike gaming keyboard. Features responsive mechanical switches (choice of Red, Blue, or Brown), full per-key RGB backlighting, a detachable wrist rest, and dedicated media controls. N-key rollover and anti-ghosting ensure every keystroke registers.', 119.99, 150, 140, '2024-04-01 12:00:00', 0),
('Gourmet Master 8-Piece Chef\'s Knife Set', 'Elevate your culinary skills with this professional 8-piece knife set. Forged from high-carbon German stainless steel for exceptional sharpness and durability. Includes chef’s knife, bread knife, santoku, utility, paring knives, honing steel, and a stylish wooden block.', 199.00, 100, 90, '2024-04-15 13:30:00', 0);

-- -----------------------------------------------------
-- Table `Account`
-- `email` VARCHAR(255), `password` VARCHAR(255), `firstname` VARCHAR(50), `lastname` VARCHAR(50)
-- -----------------------------------------------------
INSERT INTO `Account` (`email`,`password`,`firstname`,`lastname`,`creationDate`,`role`,`status`) VALUES
	 ('owner@example.com','$2b$12$ylMA7etilb3SgU1.u0kFq.1.bG.AjJOr5LRiIs5opeA3oMuJD.6MG','Owner','Account','2025-06-03 12:31:22','owner','active'),
	 ('employee@example.com','$2b$12$XIl1CHj8sSoYa2CIxdnY7.cNhe.CfFprQ6cavco.wqqzbaz.iTMl2','Emily','Ployee','2025-06-03 21:06:06','employee','active'),
	 ('admin@example.com','$2b$12$tFk05HaXEgTFymypVz3ppO3iaBF4RqT7PpwXovU62LPbSVrRaK7Kq','Adam','Nistrator','2025-06-03 21:06:06','admin','active'),
	 ('customer@example.com','$2b$12$eh7vq6/BKJpR/2lsnF8rauhmHV.wSc01WlqmC0a7HRnk5V2TBg/ue','Chris','Tommer','2025-06-03 21:06:06','customer','active'),
   ('janedoe.customer@example.com','$2b$12$fO9iGDRCRzFr3zWiqk.hA.Lp7QYMGmxHyV60Cwsdq7tY7PzY.xY/S','Jane','Doe','2024-05-01 10:00:00','customer','active'),
   ('guest.user.temp@example.com','$2b$12$NotARealHashButLooksLikeIt/123456789012345678901234567890','Guest','User','2024-05-15 14:30:00','guest','unverified'),
   ('inactive.customer.profile@example.com','$2b$12$AnotherFakeHashValueHereOkayOKThenThisIsIt','Inactive','Person','2023-11-20 08:00:00','customer','inactive'),
   ('new.customer.signup@example.com','$2b$12$YetAnotherSecurePasswordHashValueHereOkayOK','Newbie','Shopper','2024-06-01 11:00:00','customer','unverified');
-- Account IDs should be 1 through 8

-- -----------------------------------------------------
-- Table `Address`
-- `accountID` INT, `location` VARCHAR(255)
-- -----------------------------------------------------
INSERT INTO `Address` (`accountID`, `location`) VALUES
(1, '1 Owner\'s Grand Plaza, Suite 100, Capital City, CC 10001, United States'),
(2, '2 Employee Residence Way, Apartment 2B, Workville Suburb, WV 20002, United States'),
(3, '3 Administrator Central Avenue, Penthouse Suite, Control Panel City, CP 30003, United States'),
(4, '4 Customer Drive, Unit 12, Shoppersburg Town, SB 40004, United States'),
(4, 'PO Box 5678, Shoppersburg Town Post Office, SB 40005, United States'), -- Second address for customer 4
(5, '5 Another Place, Building C, Apartment 301, New Townsville, NT 50005, United States'),
(7, '7 Old Mill Lane, Historic District, Past Town City, PT 70007, United States'),
(8, '8 Fresh Start Road, Greenfield Community, Welcome City, WC 80008, United States');
-- Address IDs should be 1 through 8

-- -----------------------------------------------------
-- Table `LineItem`
-- -----------------------------------------------------
INSERT INTO `LineItem` (`productID`, `quantity`, `priceAtSale`) VALUES
(1, 1, NULL), -- For Trolley (Account 4 - Chris) -> LI ID 1
(2, 2, NULL), -- For Trolley (Account 4 - Chris) -> LI ID 2
(3, 1, NULL), -- For Trolley (Account 5 - Jane) -> LI ID 3
(7, 1, NULL), -- For Trolley (Account 5 - Jane) -> LI ID 4

(4, 1, 199.50),  -- For Order 1 (Account 4 - Chris, Address 4) -> LI ID 5
(5, 1, 135.00), -- For Order 1 (Account 4 - Chris, Address 4) -> LI ID 6

(6, 1, 249.99), -- For Order 2 (Account 5 - Jane, Address 6) -> LI ID 7
(8, 2, 199.00), -- For Order 2 (Account 5 - Jane, Address 6) -> LI ID 8 (price per unit)

(1, 1, 1899.99), -- For Order 3 (Account 2 - Emily, Address 2) -> LI ID 9
(2, 3, 69.99),   -- For Order 3 (Account 2 - Emily, Address 2) -> LI ID 10

(3, 2, NULL), -- For Trolley (Account 2 - Emily) -> LI ID 11
(4, 1, NULL), -- For Trolley (Account 7 - Inactive, but still has a trolley) -> LI ID 12

(5, 1, 135.00), -- For Order 4 (Account 7 - Inactive, past order, Address 7) -> LI ID 13
(7, 1, 119.99),  -- For Order 5 (Account 4 - Chris, Address 5 - PO Box) -> LI ID 14
(8, 1, NULL); -- For Trolley (Account 8 - Newbie) -> LI ID 15
-- LineItem IDs should be 1 through 15

-- -----------------------------------------------------
-- Table `Order`
-- -----------------------------------------------------
INSERT INTO `Order` (`accountID`, `addressID`, `date`) VALUES
(4, 4, '2024-05-10 10:00:00'), -- Order ID 1 (Uses LI 5, 6)
(5, 6, '2024-05-12 11:30:00'), -- Order ID 2 (Uses LI 7, 8)
(2, 2, '2024-05-18 14:15:00'), -- Order ID 3 (Uses LI 9, 10)
(7, 7, '2024-04-01 09:00:00'), -- Order ID 4 (Uses LI 13)
(4, 5, '2024-05-20 16:45:00'), -- Order ID 5 (Uses LI 14)
(1, 1, '2024-05-21 10:00:00'), -- Order ID 6 (Owner's order)
(8, 8, '2024-06-02 12:00:00'); -- Order ID 7 (Newbie's first order)
-- Order IDs should be 1 through 7

-- -----------------------------------------------------
-- Table `Invoice`
-- `data` BLOB
-- -----------------------------------------------------
INSERT INTO `Invoice` (`accountID`, `orderID`, `creationDate`, `data`) VALUES
(4, 1, '2024-05-10 10:05:00', 'Invoice data for order 1, Account 4 (Chris Tommer). Items: Smart Coffee Maker, TrailBlazer Shoes.'),
(5, 2, '2024-05-12 11:35:00', 'Invoice data for order 2, Account 5 (Jane Doe). Items: AllWeather Tent, Gourmet Knife Set.'),
(2, 3, '2024-05-18 14:20:00', 'Invoice data for order 3, Account 2 (Emily Ployee). Items: UltraSlim Laptop, Precision Mouse (x3).'),
(7, 4, '2024-04-01 09:05:00', 'Invoice data for order 4, Account 7 (Inactive Person). Item: TrailBlazer Shoes.'),
(4, 5, '2024-05-20 16:50:00', 'Invoice data for order 5, Account 4 (Chris Tommer). Item: StealthStrike Keyboard.'),
(1, 6, '2024-05-21 10:05:00', 'Invoice data for order 6, Account 1 (Owner Account). Internal order.'),
(8, 7, '2024-06-02 12:05:00', 'Invoice data for order 7, Account 8 (Newbie Shopper). First purchase!');
-- Invoice IDs should be 1 through 7

-- -----------------------------------------------------
-- Table `Receipt`
-- `data` BLOB
-- -----------------------------------------------------
INSERT INTO `Receipt` (`accountID`, `orderID`, `creationDate`, `data`) VALUES
(4, 1, '2024-05-10 10:06:00', 'Receipt for order 1. Thank you Chris Tommer!'),
(5, 2, '2024-05-12 11:36:00', 'Receipt for order 2. Thank you Jane Doe!'),
(2, 3, '2024-05-18 14:21:00', 'Receipt for order 3. Thank you Emily Ployee!'),
(7, 4, '2024-04-01 09:06:00', 'Receipt for order 4. Thank you Inactive Person!'),
(4, 5, '2024-05-20 16:51:00', 'Receipt for order 5. Thank you Chris Tommer!'),
(1, 6, '2024-05-21 10:06:00', 'Receipt for order 6. Internal record.'),
(8, 7, '2024-06-02 12:06:00', 'Receipt for order 7. Welcome Newbie Shopper!');
-- Receipt IDs should be 1 through 7

-- -----------------------------------------------------
-- Table `Report`
-- `data` BLOB
-- -----------------------------------------------------
INSERT INTO `Report` (`creator`, `creationDate`, `data`) VALUES
(1, '2024-06-01 09:00:00', 'Detailed Monthly Sales Performance Report - May 2024. Generated by Owner Account.'),
(3, '2024-06-01 10:00:00', 'Comprehensive User Activity and Engagement Metrics - May 2024. Generated by Adam Nistrator (Admin).'),
(1, '2024-05-01 09:00:00', 'Detailed Monthly Sales Performance Report - April 2024. Generated by Owner Account.'),
(2, '2024-06-02 11:00:00', 'Current Inventory Stock Levels and Reorder Recommendations - June 2024. Generated by Emily Ployee.'),
(3, '2024-06-03 14:00:00', 'System Health and Performance Monitoring Report - Week 22, 2024. Generated by Adam Nistrator (Admin).'),
(1, '2024-04-02 09:00:00', 'Quarterly Business Review and Strategic Outlook - Q1 2024. Generated by Owner Account.');
-- Report IDs should be 1 through 6 (creator is accountID)

-- Weak entities (Junction Tables)

-- -----------------------------------------------------
-- Table `Product-Tag`
-- -----------------------------------------------------
INSERT INTO `Product-Tag` (`productID`, `tagID`) VALUES
(1, 1), -- UltraSlim Laptop Pro 15.6" -> Electronics
(1, 6), -- UltraSlim Laptop Pro 15.6" -> PC Gaming Peripherals (can be used for gaming)
(2, 1), -- Precision Wireless Ergonomic Mouse -> Electronics
(2, 6), -- Precision Wireless Ergonomic Mouse -> PC Gaming Peripherals
(3, 2), -- The Future of Code: AI in Development -> Books & Literature
(4, 1), -- Smart Bean-to-Cup Coffee Maker -> Electronics
(4, 3), -- Smart Bean-to-Cup Coffee Maker -> Home & Kitchen Appliances
(5, 4), -- TrailBlazer Men's Running Shoes -> Fashion & Apparel
(5, 5), -- TrailBlazer Men's Running Shoes -> Sports & Outdoors Equipment
(6, 5), -- AllWeather Family Camping Tent - 6 Person -> Sports & Outdoors Equipment
(6, 8), -- AllWeather Family Camping Tent - 6 Person -> Travel Essentials
(7, 1), -- StealthStrike RGB Mechanical Gaming Keyboard -> Electronics
(7, 6), -- StealthStrike RGB Mechanical Gaming Keyboard -> PC Gaming Peripherals
(8, 3); -- Gourmet Master 8-Piece Chef's Knife Set -> Home & Kitchen Appliances

-- -----------------------------------------------------
-- Table `Product-Image`
-- -----------------------------------------------------
INSERT INTO `Product-Image` (`productID`, `imageID`) VALUES
(1, 1),  -- UltraSlim Laptop Pro 15.6"
(1, 9),  -- UltraSlim Laptop Pro 15.6" (Alt View)
(2, 2),  -- Precision Wireless Ergonomic Mouse
(3, 3),  -- The Future of Code: AI in Development
(4, 4),  -- Smart Bean-to-Cup Coffee Maker
(4, 10), -- Smart Bean-to-Cup Coffee Maker (Lifestyle)
(5, 5),  -- TrailBlazer Men's Running Shoes
(6, 6),  -- AllWeather Family Camping Tent - 6 Person
(7, 7),  -- StealthStrike RGB Mechanical Gaming Keyboard
(8, 8);  -- Gourmet Master 8-Piece Chef's Knife Set

-- -----------------------------------------------------
-- Table `Trolley`
-- -----------------------------------------------------
-- LineItem IDs for trolley: 1, 2, 3, 4, 11, 12, 15
INSERT INTO `Trolley` (`accountID`, `lineItemID`) VALUES
(4, 1), -- Customer 4 (Chris), LI 1 (Product 1 - Laptop)
(4, 2), -- Customer 4 (Chris), LI 2 (Product 2 - Mouse)
(5, 3), -- Customer 5 (Jane), LI 3 (Product 3 - Book)
(5, 4), -- Customer 5 (Jane), LI 4 (Product 7 - Keyboard)
(2, 11), -- Employee (Emily), LI 11 (Product 3 - Book)
(7, 12), -- Inactive Customer, LI 12 (Product 4 - Coffee Maker)
(8, 15); -- Newbie Shopper, LI 15 (Product 8 - Knife Set)

-- -----------------------------------------------------
-- Table `OrderItem`
-- -----------------------------------------------------
-- Order 1 (ID 1) uses LI 5, 6
-- Order 2 (ID 2) uses LI 7, 8
-- Order 3 (ID 3) uses LI 9, 10
-- Order 4 (ID 4) uses LI 13
-- Order 5 (ID 5) uses LI 14
INSERT INTO `OrderItem` (`orderID`, `lineItemID`) VALUES
(1, 5),
(1, 6),
(2, 7),
(2, 8),
(3, 9),
(3, 10),
(4, 13),
(5, 14);

-- For Order 6 (Owner), let's add a new LineItem and then link it.
INSERT INTO `LineItem` (`productID`, `quantity`, `priceAtSale`) VALUES (8, 1, 199.00); -- LI ID 16
INSERT INTO `OrderItem` (`orderID`, `lineItemID`) VALUES (6, 16);

-- For Order 7 (Newbie), let's add a new LineItem and then link it.
INSERT INTO `LineItem` (`productID`, `quantity`, `priceAtSale`) VALUES (5, 1, 135.00); -- LI ID 17
INSERT INTO `OrderItem` (`orderID`, `lineItemID`) VALUES (7, 17);


COMMIT;
