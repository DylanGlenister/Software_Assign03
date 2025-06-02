# Active: 1747886189739@@127.0.0.1@3306@awe_electronics
# No transaction as the whole point of this file is to overwrite the database

# Overwrite existing tables
DROP TABLE IF EXISTS `OrderItem`;
DROP TABLE IF EXISTS `Trolley`;
DROP TABLE IF EXISTS `Product-Image`;
DROP TABLE IF EXISTS `Product-Tag`;
DROP TABLE IF EXISTS `Report`;
DROP TABLE IF EXISTS `Receipt`;
DROP TABLE IF EXISTS `Invoice`;
DROP TABLE IF EXISTS `LineItem`;
DROP TABLE IF EXISTS `Order`;
DROP TABLE IF EXISTS `Address`;
DROP TABLE IF EXISTS `Account`;
DROP TABLE IF EXISTS `Product`;
DROP TABLE IF EXISTS `Image`;
DROP TABLE IF EXISTS `Tag`;
DROP TABLE IF EXISTS `Status`;
DROP TABLE IF EXISTS `Role`;

# Start node tables
# (Tables that contain no foreign keys and are referenced as foreign keys in other tables)

CREATE TABLE `Tag` (
	`tagID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`name` VARCHAR(32) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `Image` (
	`imageID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`url` VARCHAR(32) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE `Product` (
	`productID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`name` VARCHAR(100) NOT NULL,
	`description` VARCHAR(200) NOT NULL,
	`price` FLOAT NOT NULL,
	`stock` INT NOT NULL COMMENT 'This is the quantity of this product currently held.',
	`available` INT NOT NULL COMMENT 'This is the quantity of this product available for purchase.',
	`creationDate` DATETIME NOT NULL,
	`discontinued` INT(2) NOT NULL COMMENT 'Is this item no longer being sold.'
) ENGINE=InnoDB;

# Intermediate node tables
# (Tables that contain foreign keys and are referenced as foreign keys in other tables)

CREATE TABLE `Account` (
	`accountID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`email` VARCHAR(100) NOT NULL,
	`password` VARCHAR(100) NOT NULL,
	`firstname` VARCHAR(50) DEFAULT NULL,
	`lastname` VARCHAR(50) DEFAULT NULL,
	`creationDate` DATETIME NOT NULL,
	`role` enum('owner', 'admin', 'employee', 'customer', 'guest') NOT NULL DEFAULT 'guest',
	`status` enum('unverified', 'active', 'inactive', 'condemned') NOT NULL DEFAULT 'unverified'
) ENGINE=InnoDB;

CREATE TABLE `Address` (
	`addressID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`accountID` INT NOT NULL,
	`location` VARCHAR(150) NOT NULL,
	CONSTRAINT `address_FK_account` FOREIGN KEY (`accountID`) REFERENCES `Account` (`accountID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `Order` (
	`orderID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`accountID` INT NOT NULL,
	`addressID` INT NOT NULL,
	`date` DATETIME NOT NULL,
	CONSTRAINT `order_FK_account` FOREIGN KEY (`accountID`) REFERENCES `Account` (`accountID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `order_FK_address` FOREIGN KEY (`addressID`) REFERENCES `Address` (`addressID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `LineItem` (
	`lineItemID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`productID` INT NOT NULL,
	`quantity` INT NOT NULL,
	`priceAtSale` FLOAT DEFAULT NULL,
	CONSTRAINT `lineItem_FK_product` FOREIGN KEY (`productID`) REFERENCES `Product` (`productID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

# End node tables
# (Tables that contain foreign keys and are not referenced as foreign keys in other tables)

CREATE TABLE `Invoice` (
	`invoiceID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`accountID` INT NOT NULL,
	`orderID` INT NOT NULL,
	`creationDate` DATETIME NOT NULL,
	`data` BLOB NOT NULL,
	CONSTRAINT `invoice_FK_account` FOREIGN KEY (`accountID`) REFERENCES `Account` (`accountID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `invoice_FK_order` FOREIGN KEY (`orderID`) REFERENCES `Order` (`orderID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `Receipt` (
	`receiptID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`accountID` INT NOT NULL,
	`orderID` INT NOT NULL,
	`creationDate` DATETIME NOT NULL,
	`data` BLOB NOT NULL,
	CONSTRAINT `receipt_FK_account` FOREIGN KEY (`accountID`) REFERENCES `Account` (`accountID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `receipt_FK_order` FOREIGN KEY (`orderID`) REFERENCES `Order` (`orderID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `Report` (
	`reportID` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`creator` INT NOT NULL COMMENT 'AccountID',
	`creationDate` DATETIME NOT NULL,
	`data` BLOB NOT NULL,
	CONSTRAINT `report_FK_account` FOREIGN KEY (`creator`) REFERENCES `Account` (`accountID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

# Weak entities

CREATE TABLE `Product-Tag` (
	`productID` INT NOT NULL,
	`tagID` INT NOT NULL,
	PRIMARY KEY (`productID`, `tagID`),
	CONSTRAINT `product-tag_FK_product` FOREIGN KEY (`productID`) REFERENCES `Product` (`productID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `product-tag_FK_tag` FOREIGN KEY (`tagID`) REFERENCES `Tag` (`tagID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `Product-Image` (
	`productID` INT NOT NULL,
	`imageID` INT NOT NULL,
	PRIMARY KEY (`productID`, `imageID`),
	CONSTRAINT `product-image_FK_product` FOREIGN KEY (`productID`) REFERENCES `Product` (`productID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `product-image_FK_image` FOREIGN KEY (`imageID`) REFERENCES `Image` (`imageID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `Trolley` (
	`accountID` INT NOT NULL,
	`lineItemID` INT NOT NULL,
	PRIMARY KEY (`accountID`, `lineItemID`),
	CONSTRAINT `trolley_FK_account` FOREIGN KEY (`accountID`) REFERENCES `Account` (`accountID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `trolley_FK_lineItem` FOREIGN KEY (`lineItemID`) REFERENCES `LineItem` (`lineItemID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE `OrderItem` (
	`orderID` INT NOT NULL,
	`lineItemID` INT NOT NULL,
	PRIMARY KEY (`orderID`, `lineItemID`),
	CONSTRAINT `order-item_FK_account` FOREIGN KEY (`orderID`) REFERENCES `Order` (`orderID`) ON DELETE RESTRICT ON UPDATE RESTRICT,
	CONSTRAINT `order-item_FK_lineItem` FOREIGN KEY (`lineItemID`) REFERENCES `LineItem` (`lineItemID`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;
