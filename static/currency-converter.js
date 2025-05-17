/**
 * Currency conversion utility for NotoAI
 * Converts prices from USD to local currency based on user's location
 */

class CurrencyConverter {
    constructor() {
        this.exchangeRates = {};
        this.userCurrency = 'USD'; // Default currency
        this.initialized = false;
    }

    /**
     * Initialize the currency converter
     * Fetches user's location and exchange rates
     */
    async initialize() {
        try {
            // Get user's country and currency
            await this.detectUserLocation();
            // Fetch exchange rates
            await this.fetchExchangeRates();
            this.initialized = true;
            return true;
        } catch (error) {
            console.error('Currency converter initialization failed:', error);
            return false;
        }
    }

    /**
     * Detect user's location using IP geolocation
     */
    async detectUserLocation() {
        try {
            const response = await fetch('https://ipapi.co/json/');
            if (!response.ok) throw new Error('Failed to detect location');
            
            const data = await response.json();
            this.userCountry = data.country_name;
            this.userCurrency = data.currency;
            
            console.log(`User location detected: ${this.userCountry}, Currency: ${this.userCurrency}`);
            return this.userCurrency;
        } catch (error) {
            console.error('Location detection failed:', error);
            this.userCurrency = 'USD'; // Fallback to USD
            return this.userCurrency;
        }
    }

    /**
     * Fetch latest exchange rates from ExchangeRate-API
     */
    async fetchExchangeRates() {
        try {
            // Using free exchange rate API
            const response = await fetch(`https://open.er-api.com/v6/latest/USD`);
            if (!response.ok) throw new Error('Failed to fetch exchange rates');
            
            const data = await response.json();
            this.exchangeRates = data.rates;
            this.lastUpdated = new Date(data.time_last_update_utc);
            
            console.log('Exchange rates fetched successfully');
            return this.exchangeRates;
        } catch (error) {
            console.error('Exchange rate fetch failed:', error);
            this.exchangeRates = {}; // Reset rates on failure
            return {};
        }
    }

    /**
     * Convert price from USD to user's local currency
     * @param {number} usdPrice - Price in USD (in cents)
     * @returns {object} - Converted price information
     */
    convertPrice(usdPrice) {
        if (!this.initialized || !this.exchangeRates[this.userCurrency]) {
            return {
                price: usdPrice / 100, // Convert cents to dollars
                currency: 'USD',
                symbol: '$',
                originalPrice: usdPrice
            };
        }

        // Convert from USD cents to local currency
        const rate = this.exchangeRates[this.userCurrency];
        const convertedPrice = (usdPrice / 100) * rate;
        
        // Format price and determine symbol
        const formattedPrice = this.formatPrice(convertedPrice);
        const currencySymbol = this.getCurrencySymbol(this.userCurrency);
        
        return {
            price: formattedPrice,
            currency: this.userCurrency,
            symbol: currencySymbol,
            originalPrice: usdPrice,
            rate: rate
        };
    }

    /**
     * Format price to appropriate decimal places
     * @param {number} price - Price to format
     * @returns {number} - Formatted price
     */
    formatPrice(price) {
        // Special handling for JPY and currencies that don't use decimals
        if (this.userCurrency === 'JPY' || this.userCurrency === 'KRW') {
            return Math.round(price);
        }
        
        // For other currencies, round to 2 decimal places
        return Math.round(price * 100) / 100;
    }

    /**
     * Get currency symbol for display
     * @param {string} currencyCode - ISO currency code
     * @returns {string} - Currency symbol
     */
    getCurrencySymbol(currencyCode) {
        const currencySymbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'INR': '₹',
            'JPY': '¥',
            'AUD': 'A$',
            'CAD': 'C$',
            'CNY': '¥',
            'HKD': 'HK$',
            'RUB': '₽',
            'BRL': 'R$',
            'ZAR': 'R',
            'SGD': 'S$',
            'NZD': 'NZ$'
            // Add more currency symbols as needed
        };
        
        return currencySymbols[currencyCode] || currencyCode;
    }
}

// Export the currency converter instance
const currencyConverter = new CurrencyConverter();
export default currencyConverter;
