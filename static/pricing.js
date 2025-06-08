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
    const paypalButtonContainer = document.getElementById('paypal-button-container'); // Updated for PayPal
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
        console.log('[Pricing] handleSubscription called with planId:', planId);
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
                console.error('Error subscribing to free plan:', error);
                showToast(error.message, 'error');
            }
            return;
        }

        // For paid plans, show payment modal and render PayPal buttons
        try {
            // Clear any existing PayPal buttons
            console.log('[Pricing] Handling paid plan. PayPal button container:', paypalButtonContainer);
            if (paypalButtonContainer) {
                paypalButtonContainer.innerHTML = '';
            } else {
                console.error('[Pricing] paypal-button-container not found!');
                showToast('Internal error: PayPal container missing.', 'error');
                return;
            }
            
            // Fetch plan details
            const planDetailsResponse = await fetch(`/api/get-plan-details/${planId}`);
            if (!planDetailsResponse.ok) {
                console.error('[Pricing] Failed to fetch plan details:', planDetailsResponse.status, await planDetailsResponse.text());
                throw new Error('Could not fetch plan details.');
            }
            console.log('[Pricing] Plan details fetched successfully.');
            const planData = await planDetailsResponse.json();

            paymentPlanName.textContent = `Subscribe to ${planData.name}`;
            const priceInUSD = (planData.price / 100).toFixed(2);
            
            // Show the price in local currency if available
            if (currencyConverter.initialized && currencyConverter.userCurrency !== 'USD') {
                const convertedPrice = currencyConverter.convertPrice(planData.price);
                let priceDisplayP = document.querySelector('.dynamic-price-display');
                if (!priceDisplayP) {
                    priceDisplayP = document.createElement('p');
                    priceDisplayP.className = 'dynamic-price-display';
                    // Insert after the h2 (paymentPlanName) and before paypal-button-container
                    paypalButtonContainer.parentNode.insertBefore(priceDisplayP, paypalButtonContainer);
                }
                priceDisplayP.innerHTML = `Amount: <span style="font-weight:bold;">${convertedPrice.symbol}${convertedPrice.price}</span> (${currencyConverter.userCurrency})<br><small>(Approx. USD ${priceInUSD} - Payment processed in USD)</small>`;
            } else {
                let priceDisplayP = document.querySelector('.dynamic-price-display');
                if (!priceDisplayP) {
                    priceDisplayP = document.createElement('p');
                    priceDisplayP.className = 'dynamic-price-display';
                    paypalButtonContainer.parentNode.insertBefore(priceDisplayP, paypalButtonContainer);
                }
                priceDisplayP.innerHTML = `Amount: <span style="font-weight:bold;">$${priceInUSD}</span> USD`;
            }
            
            // Show the modal
            console.log('[Pricing] Payment modal element:', paymentModal);
            if (paymentModal) {
                paymentModal.style.display = 'block';
                console.log('[Pricing] Payment modal display set to block.');
            } else {
                console.error('[Pricing] payment-modal not found!');
                showToast('Internal error: Payment modal missing.', 'error');
                return;
            }
            
            // Initialize PayPal button
            console.log('[Pricing] Checking for window.paypal:', window.paypal);
            if (window.paypal) {
                console.log('[Pricing] Calling renderPayPalButton.');
                renderPayPalButton(planId, planData);
            } else {
                console.error('PayPal SDK not loaded. Please refresh.');
                showToast('Error loading PayPal. Please refresh the page and try again.', 'error');
                console.log('[Pricing] PayPal SDK not loaded, toast shown.');
            }
        } catch (error) {
            console.error('Error in handleSubscription (paid plan):', error);
            showToast(error.message || 'Could not initiate subscription. Please try again.', 'error');
            paymentModal.style.display = 'none';
        }
    }
    
    function renderPayPalButton(planId, planData) {
        paypal.Buttons({
            createOrder: function(data, actions) {
                // Set up the transaction
                return fetch('/api/create-subscription', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        plan_id: planId
                    })
                })
                .then(function(response) {
                    return response.json();
                })
                .then(function(orderData) {
                    if (!orderData.approval_url) {
                        throw new Error('No approval URL received from server');
                    }
                    return orderData.approval_url.split('token=')[1]; // Return the order ID
                });
            },
            onApprove: function(data, actions) {
                // This function captures the funds from the transaction
                return fetch(`/api/verify-payment`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        payment_id: data.orderID,
                        plan_id: planId
                    })
                })
                .then(function(response) {
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.error || 'Payment verification failed'); });
                    }
                    return response.json();
                })
                .then(function(details) {
                    // Show a success message to the buyer
                    showToast('Payment successful! Your subscription has been activated.', 'success');
                    
                    // Close the payment modal
                    paymentModal.style.display = 'none';
                    
                    // Redirect to dashboard or reload the page after a short delay
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 2000);
                })
                .catch(function(err) {
                    console.error('Payment verification error:', err);
                    showToast(err.message || 'Error processing your payment. Please try again.', 'error');
                });
            },
            onError: function(err) {
                console.error('PayPal error:', err);
                showToast('An error occurred with PayPal. Please try again.', 'error');
            },
            onCancel: function(data) {
                // Show a cancel page, or return to cart
                showToast('Payment was cancelled.', 'error');
            }
        }).render('#paypal-button-container');
    }

    function showToast(message, type = 'success') {
        toast.textContent = message;
        toast.className = 'toast show' + (type === 'error' ? ' error' : '');
        
        // Hide toast after 5 seconds
        setTimeout(() => {
            toast.className = toast.className.replace(' show', '');
        }, 5000);
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

                // Add disclaimer about USD processing
                let disclaimer = element.querySelector('.usd-disclaimer');
                if (!disclaimer) {
                    disclaimer = document.createElement('small');
                    disclaimer.className = 'usd-disclaimer';
                    disclaimer.style.display = 'block';
                    disclaimer.style.fontSize = '0.8em';
                    disclaimer.style.color = '#666';
                    disclaimer.style.marginTop = '5px';
                    // Insert after the pricing-amount's parent or a suitable location
                    element.parentNode.appendChild(disclaimer); 
                }
                const priceInUSD = (originalPrice / 100).toFixed(2);
                disclaimer.innerHTML = `(Approx. USD ${priceInUSD} - Payment processed in USD)`;
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
