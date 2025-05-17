// Pricing page with Razorpay integration
import currencyConverter from './currency-converter.js';

document.addEventListener('DOMContentLoaded', async function() {
    // Initialize currency converter
    await currencyConverter.initialize();
    
    // Convert all prices to local currency
    updatePricesToLocalCurrency();
    // Elements
    const subscribeButtons = document.querySelectorAll('.subscribe-btn');
    const paymentModal = document.getElementById('payment-modal');
    const closeModal = document.querySelector('.close-modal');
    const paymentPlanName = document.getElementById('payment-plan-name');
    const paymentAmount = document.getElementById('payment-amount');
    const razorpayContainer = document.getElementById('razorpay-container');
    const toast = document.getElementById('toast');
    
    // Event listeners
    subscribeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const planId = this.dataset.planId;
            handleSubscription(planId);
        });
    });
    
    closeModal.addEventListener('click', function() {
        paymentModal.style.display = 'none';
    });
    
    // Click outside modal to close
    window.addEventListener('click', function(event) {
        if (event.target === paymentModal) {
            paymentModal.style.display = 'none';
        }
    });
    
    // Functions
    async function handleSubscription(planId) {
        if (planId === 'free') {
            try {
                const response = await fetch('/api/create-subscription', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ plan_id: planId }),
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to subscribe to plan');
                }
                
                const data = await response.json();
                showToast(data.message, 'success');
                
                // Reload page after successful subscription
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
                
            } catch (error) {
                console.error('Error:', error);
                showToast(error.message, 'error');
            }
            
            return;
        }
        
        // For paid plans, create an order and show payment modal
        try {
            const response = await fetch('/api/create-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ plan_id: planId }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to create subscription');
            }
            
            const data = await response.json();
            
            // Update modal content
            paymentPlanName.textContent = `Subscribe to ${data.product_name}`;
            
            // Convert price to local currency for display but clearly show USD amount for payment
            if (currencyConverter.initialized && currencyConverter.userCurrency !== 'USD') {
                const convertedPrice = currencyConverter.convertPrice(data.amount);
                
                // Clear previous content in payment details
                const paymentDetails = document.querySelector('.payment-details');
                
                // Create styled elements for price display
                const priceDisplay = document.createElement('div');
                priceDisplay.className = 'price-display';
                priceDisplay.style.margin = '20px 0';
                
                // Local currency display (for reference)
                const localPriceDiv = document.createElement('div');
                localPriceDiv.className = 'local-price';
                localPriceDiv.innerHTML = `<span style="font-size:0.9em; color:#666;">Price in your currency (for reference):</span><br>
                    <span style="font-size:1.4em; font-weight:600;">${convertedPrice.symbol}${convertedPrice.price}</span> <span class="currency-badge" style="font-size:0.7em; padding:2px 5px; border-radius:3px; background-color:rgba(98,0,234,0.1); color:#6200EA;">${currencyConverter.userCurrency}</span>`;
                priceDisplay.appendChild(localPriceDiv);
                
                // Divider
                const divider = document.createElement('div');
                divider.style.margin = '15px 0';
                divider.style.borderBottom = '1px solid #eee';
                priceDisplay.appendChild(divider);
                
                // USD amount (actual charge)
                const usdPriceDiv = document.createElement('div');
                usdPriceDiv.className = 'usd-price';
                usdPriceDiv.innerHTML = `<span style="font-size:0.9em; font-weight:600; color:#333;">You will be charged:</span><br>
                    <span style="font-size:1.6em; font-weight:700; color:#6200EA;">$${data.amount / 100} USD</span>`;
                priceDisplay.appendChild(usdPriceDiv);
                
                // Important note
                const paymentNote = document.createElement('p');
                paymentNote.className = 'payment-note';
                paymentNote.innerHTML = `<i>Note: Your card will be charged in USD. Your bank may apply their own exchange rate.</i>`;
                paymentNote.style.fontSize = '0.8em';
                paymentNote.style.color = '#666';
                paymentNote.style.marginTop = '15px';
                
                // Replace payment amount display
                paymentAmount.style.display = 'none';
                paymentDetails.insertBefore(priceDisplay, paymentDetails.firstChild);
                paymentDetails.appendChild(paymentNote);
            } else {
                paymentAmount.textContent = `$${data.amount / 100} USD`;
            }
            
            // Show payment modal
            paymentModal.style.display = 'block';
            
            // Create Razorpay button
            const options = {
                key: data.key_id,
                amount: data.amount,
                currency: data.currency,
                name: 'NotoAI',
                description: data.description,
                order_id: data.order_id,
                handler: function(response) {
                    verifyPayment(response, planId);
                },
                prefill: {
                    name: data.user_info.name,
                    email: data.user_info.email,
                    contact: data.user_info.contact
                },
                theme: {
                    color: '#6200EA'
                }
            };
            
            const rzp = new Razorpay(options);
            
            // Clear previous button
            razorpayContainer.innerHTML = '';
            
            // Create button
            const payButton = document.createElement('button');
            payButton.textContent = 'Pay Now';
            payButton.className = 'razorpay-btn';
            payButton.addEventListener('click', function() {
                rzp.open();
                paymentModal.style.display = 'none';
            });
            
            razorpayContainer.appendChild(payButton);
            
        } catch (error) {
            console.error('Error:', error);
            showToast(error.message, 'error');
        }
    }
    
    async function verifyPayment(response, planId) {
        try {
            const verifyData = {
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
                plan_id: planId
            };
            
            const verifyResponse = await fetch('/api/verify-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(verifyData),
            });
            
            if (!verifyResponse.ok) {
                const errorData = await verifyResponse.json();
                throw new Error(errorData.error || 'Payment verification failed');
            }
            
            const data = await verifyResponse.json();
            showToast(data.message, 'success');
            
            // Reload page after successful payment
            setTimeout(() => {
                window.location.reload();
            }, 2000);
            
        } catch (error) {
            console.error('Error:', error);
            showToast(error.message, 'error');
        }
    }
    
    function showToast(message, type = 'success') {
        toast.textContent = message;
        toast.className = 'toast';
        toast.classList.add(type);
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    /**
     * Updates all prices on the pricing page to the user's local currency
     */
    function updatePricesToLocalCurrency() {
        if (!currencyConverter.initialized) return;
        
        // Skip conversion if already in USD
        if (currencyConverter.userCurrency === 'USD') return;
        
        // Update all price displays on the page
        const priceElements = document.querySelectorAll('.pricing-amount');
        
        priceElements.forEach(element => {
            // Get the amount element and its value
            const amountEl = element.querySelector('.amount');
            const currencyEl = element.querySelector('.currency');
            
            if (!amountEl || !currencyEl) return;
            
            // Extract original price in USD
            const originalPrice = parseInt(amountEl.textContent) * 100; // Convert to cents
            
            // For free tier, just update the currency symbol but keep price at 0
            if (originalPrice === 0) {
                // Update currency symbol for free plan as well for consistency
                currencyEl.textContent = currencyConverter.getCurrencySymbol(currencyConverter.userCurrency);
                return;
            }
            
            // Convert price to local currency
            const convertedPrice = currencyConverter.convertPrice(originalPrice);
            
            // Update display
            amountEl.textContent = convertedPrice.price;
            currencyEl.textContent = convertedPrice.symbol;
            
            // Apply cleaner styling for currency display
            // Update with modern styling for the currency and amount
            element.classList.add('localized-price');
            
            // Create a small badge to indicate the conversion
            const currencyBadge = document.createElement('span');
            currencyBadge.className = 'currency-badge';
            currencyBadge.textContent = currencyConverter.userCurrency;
            currencyBadge.style.fontSize = '0.6em';
            currencyBadge.style.padding = '2px 5px';
            currencyBadge.style.borderRadius = '3px';
            currencyBadge.style.backgroundColor = 'rgba(98, 0, 234, 0.1)';
            currencyBadge.style.color = '#6200EA';
            currencyBadge.style.marginLeft = '5px';
            currencyBadge.style.verticalAlign = 'middle';
            currencyBadge.style.display = 'inline-block';
            
            // Add it after the currency symbol
            const billingCycle = element.querySelector('.billing-cycle');
            if (billingCycle) {
                billingCycle.insertAdjacentElement('afterend', currencyBadge);
            }
        });
        
        // Add a simple, elegant currency notification
        const pricingContainer = document.querySelector('.pricing-container');
        const currencyInfoDiv = document.createElement('div');
        currencyInfoDiv.className = 'currency-info';
        
        // Create a styled notification banner with payment information
        currencyInfoDiv.innerHTML = `
            <div class="currency-notification">
                <span class="currency-icon">🌐</span>
                Prices shown in ${currencyConverter.userCurrency} based on your location. All payments are processed in USD.
            </div>
        `;
        
        // Add clean styling
        currencyInfoDiv.style.textAlign = 'center';
        currencyInfoDiv.style.marginTop = '2rem';
        
        // Style the notification banner
        const styleElement = document.createElement('style');
        styleElement.textContent = `
            .currency-notification {
                display: inline-block;
                padding: 8px 16px;
                background-color: rgba(98, 0, 234, 0.05);
                border-radius: 20px;
                font-size: 0.9em;
                color: #6e6e6e;
            }
            .currency-icon {
                margin-right: 8px;
            }
        `;
        document.head.appendChild(styleElement);
        
        // Add to the page before the footer
        pricingContainer.appendChild(currencyInfoDiv);
    }
});
