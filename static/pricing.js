// Pricing page with Razorpay integration
document.addEventListener('DOMContentLoaded', function() {
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
            paymentAmount.textContent = `₹${data.amount / 100}`;
            
            // Show payment modal
            paymentModal.style.display = 'block';
            
            // Create Razorpay button
            const options = {
                key: data.key_id,
                amount: data.amount,
                currency: data.currency,
                name: 'NOTO',
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
});
