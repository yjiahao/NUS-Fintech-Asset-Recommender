-- create all tables here first
-- sql code here
CREATE TABLE IF NOT EXISTS customers(
    customer_id VARCHAR(256) PRIMARY KEY,
    customer_type VARCHAR(256) NOT NULL,
    investment_capacity VARCHAR(256) NOT NULL,
    risk_level VARCHAR(256) NOT NULL,
    timestamp DATE
);

CREATE TABLE IF NOT EXISTS assets(
    ISIN VARCHAR(256),
    asset_short_name VARCHAR(256),
    sector VARCHAR(256),
    industry VARCHAR(256),
    timestamp DATE,
    asset_sub_category VARCHAR(256),
    asset_category VARCHAR(256) NOT NULL,
    market_id VARCHAR(256) NOT NULL,
    asset_name VARCHAR(256), -- NOT NULL
    PRIMARY KEY(ISIN)
);

CREATE TABLE IF NOT EXISTS markets(
    market_id VARCHAR(256) PRIMARY KEY,
    exchange_id VARCHAR(256) NOT NULL,
    name VARCHAR(256) NOT NULL,
    description VARCHAR(500) NOT NULL,
    country VARCHAR(256),
    trading_days VARCHAR(256) NOT NULL,
    trading_hours VARCHAR(256),
    market_class VARCHAR(256) NOT NULL
);


CREATE TABLE IF NOT EXISTS transactions(
    transaction_id VARCHAR(256),
    customer_id VARCHAR(256),
    market_id VARCHAR(256),
    ISIN VARCHAR(256),
    asset_name VARCHAR(256),
    channel VARCHAR(256) NOT NULL,
    units INT NOT NULL,
    transaction_type VARCHAR(256) NOT NULL,
    total_value NUMERIC(15, 5),
    timestamp DATE,
    PRIMARY KEY(transaction_id, customer_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE DEFERRABLE,
    FOREIGN KEY (market_id) REFERENCES markets(market_id) ON DELETE CASCADE DEFERRABLE,
    FOREIGN KEY (ISIN) REFERENCES assets(ISIN) ON DELETE CASCADE DEFERRABLE
);

-- got to do this because the csv files header names different from what we want in the db
-- create temp tables

-- CUSTOMERS TABLE
CREATE TABLE staging_customers_table (
    customerID TEXT,
    customerType TEXT,
    riskLevel TEXT,
    investmentCapacity TEXT,
    lastQuestionnaireDate TIMESTAMP,
    timestamp TIMESTAMP
);
COPY staging_customers_table FROM '/data/customer_information.csv' DELIMITER ',' CSV HEADER;

INSERT INTO customers (customer_id, customer_type, risk_level, investment_capacity, timestamp)
SELECT DISTINCT ON (customerID)
    customerID,
    customerType,
    riskLevel,
    investmentCapacity,
    timestamp
FROM staging_customers_table
ORDER BY customerID, timestamp DESC;

-- drop temp table
DROP TABLE staging_customers_table;

-- ASSETS TABLE
-- original
-- ISIN	assetName	assetShortName	assetCategory	assetSubCategory	marketID	sector	industry	timestamp	tavily_search_results	content	errors	ticker	description
CREATE TABLE staging_assets_table (
    ISIN TEXT,
    assetName TEXT,
    assetShortName TEXT,
    assetCategory TEXT,
    assetSubCategory TEXT,
    marketID TEXT,
    sector TEXT,
    industry TEXT,
    timestamp TIMESTAMP
);
COPY staging_assets_table FROM '/data/asset_information.csv' DELIMITER ',' CSV HEADER;

INSERT INTO assets (ISIN, asset_name, asset_short_name, asset_category, asset_sub_category, market_id, sector, industry, timestamp)
SELECT DISTINCT ON (ISIN)
    ISIN,
    assetName,
    assetShortName,
    assetCategory,
    assetSubCategory,
    marketID,
    sector,
    industry,
    timestamp
FROM staging_assets_table
ORDER BY ISIN, timestamp DESC;

DROP TABLE staging_assets_table;

-- MARKETS TABLE
CREATE TABLE staging_markets_table (
    exchangeID TEXT,
    marketID TEXT,
    name TEXT,
    description TEXT,
    country TEXT,
    tradingDays TEXT,
    tradingHours TEXT,
    marketClass TEXT
);
COPY staging_markets_table FROM '/data/markets.csv' DELIMITER ',' CSV HEADER;

INSERT INTO markets (exchange_id, market_id, name, description, country, trading_days, trading_hours, market_class)
SELECT exchangeID, marketID, name, description, country, tradingDays, tradingHours, marketClass
FROM staging_markets_table;

DROP TABLE staging_markets_table;

-- TRANSACTIONS TABLE
CREATE TABLE staging_transactions_table (
    customerID TEXT,
    ISIN TEXT,
    transactionID TEXT,
    transactionType TEXT,
    timestamp TIMESTAMP,
    totalValue NUMERIC,
    units NUMERIC,
    channel TEXT,
    marketID TEXT
);
COPY staging_transactions_table FROM '/data/transactions.csv' DELIMITER ',' CSV HEADER;

INSERT INTO transactions (customer_id, ISIN, transaction_id, transaction_type, timestamp, total_value, units, channel, market_id)
SELECT customerID, ISIN, transactionID, transactionType, timestamp, totalValue, units, channel, marketID
FROM staging_transactions_table;

DROP TABLE staging_transactions_table;
