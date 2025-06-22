// Dashboard functionality for YouTube video summarization
document.addEventListener('DOMContentLoaded', function() {
  // Initialize progress bars based on data-progress attributes
  const progressBars = document.querySelectorAll('.progress-bar[data-progress]');
  progressBars.forEach(bar => {
    const progressAttr = bar.getAttribute('data-progress');
    const progress = progressAttr !== null && !isNaN(parseFloat(progressAttr)) ? parseFloat(progressAttr) : 0;
    console.log('Initializing progress bar with width:', `${progress}%`);
    bar.style.width = `${progress}%`;
  });

    // Elements
    const youtubeUrlInput = document.getElementById('youtube-url');
    const summarizeBtn = document.getElementById('summarize-btn');
    const confirmSummarizeBtn = document.getElementById('confirm-summarize-btn');
    const videoPreview = document.getElementById('video-preview');
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoTitle = document.getElementById('video-title');
    const videoDuration = document.getElementById('video-duration').querySelector('span');
    
    const summaryModal = document.getElementById('summary-modal');
    const closeModal = document.querySelector('.close-modal');
    const summaryLoading = document.getElementById('summary-loading');
    const summaryContent = document.getElementById('summary-content');
    const summaryTitle = document.getElementById('summary-title');
    const summaryBody = document.getElementById('summary-body');
    
    const toast = document.getElementById('toast');
    
    // Video data storage
    let currentVideo = null;
    
    // Event listeners
    summarizeBtn.addEventListener('click', handleVideoUrlSubmit);
    confirmSummarizeBtn.addEventListener('click', generateSummary);
    closeModal.addEventListener('click', closeModalHandler);
    
    // Handle view summary buttons for recent videos
    document.querySelectorAll('.view-summary').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const videoId = this.dataset.videoId;
            fetchVideoSummary(videoId);
        });
    });
    
    // Functions
    async function handleVideoUrlSubmit() {
        const url = youtubeUrlInput.value.trim();
        
        if (!url) {
            showToast('Please enter a YouTube URL', 'error');
            return;
        }
        
        // Regular expression to check for valid YouTube URL
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})(\S*)?$/;
        if (!youtubeRegex.test(url)) {
            showToast('Please enter a valid YouTube URL', 'error');
            return;
        }
        
        // Show loading state
        summarizeBtn.textContent = 'Loading...';
        summarizeBtn.disabled = true;
        
        try {
            const response = await fetch('/api/extract-video-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ video_url: url }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to extract video information');
            }
            
            const data = await response.json();
            currentVideo = data;
            
            // Update video preview
            videoThumbnail.src = data.thumbnail;
            videoTitle.textContent = data.title;
            videoDuration.textContent = data.duration_minutes;
            
            // Show video preview
            videoPreview.classList.remove('hidden');
            
        } catch (error) {
            console.error('Error:', error);
            showToast(error.message, 'error');
        } finally {
            // Reset button state
            summarizeBtn.textContent = 'Summarize';
            summarizeBtn.disabled = false;
        }
    }
    
    async function generateSummary() {
        if (!currentVideo) {
            showToast('No video selected', 'error');
            return;
        }
        
        // Show modal with loading spinner
        summaryContent.classList.add('hidden');
        summaryLoading.classList.remove('hidden');
        summaryModal.style.display = 'block';
        
        try {
            const response = await fetch('/api/summarize-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: currentVideo.video_id,
                    video_url: youtubeUrlInput.value.trim(),
                    title: currentVideo.title,
                    channel: currentVideo.channel,
                    duration_minutes: currentVideo.duration_minutes
                }),
            });
            
            const responseData = await response.json();
            
            if (!response.ok) {
                if (responseData.error === 'Plan limit would be exceeded' && responseData.message) {
                    throw new Error(responseData.message);
                } else {
                    throw new Error(responseData.error || 'Failed to generate summary');
                }
            }
            
            // Check if processing is asynchronous
            if (responseData.processing) {
                // Handle asynchronous processing
                await handleAsyncProcessing(responseData);
            } else {
                // Handle immediate response (cached or fallback)
                displaySummary(responseData);
            }
            
        } catch (error) {
            console.error('Error generating summary:', error);
            showToast(error.message || 'Failed to generate summary', 'error');
            summaryModal.style.display = 'none';
        }
    }
    
    async function handleAsyncProcessing(jobData) {
        // Update loading message to show processing status
        const loadingText = summaryLoading.querySelector('p');
        if (loadingText) {
            loadingText.textContent = 'Processing video transcript... This may take a few minutes.';
        }
        
        // Add processing info
        const processingInfo = document.createElement('div');
        processingInfo.className = 'processing-info';
        processingInfo.innerHTML = `
            <h3>${jobData.title}</h3>
            <p><strong>Channel:</strong> ${jobData.channel}</p>
            <p><strong>Duration:</strong> ${jobData.duration_minutes} minutes</p>
            <p><strong>Status:</strong> <span id="processing-status">Processing...</span></p>
            <p><small>Job ID: ${jobData.job_id}</small></p>
        `;
        
        summaryLoading.appendChild(processingInfo);
        
        // Start polling for job completion
        const maxPollingTime = 10 * 60 * 1000; // 10 minutes
        const pollingInterval = 5000; // 5 seconds
        const startTime = Date.now();
        
        const pollJobStatus = async () => {
            try {
                const statusResponse = await fetch(`/api/check-job-status/${jobData.video_id}`);
                const statusData = await statusResponse.json();
                
                if (!statusResponse.ok) {
                    throw new Error(statusData.error || 'Failed to check job status');
                }
                
                const statusElement = document.getElementById('processing-status');
                
                if (statusData.status === 'completed') {
                    // Job completed, display the summary
                    displaySummary(statusData);
                    return;
                } else if (statusData.status === 'failed' || statusData.status === 'error') {
                    throw new Error('Video processing failed. Please try again.');
                } else {
                    // Update status display
                    if (statusElement) {
                        statusElement.textContent = `${statusData.status}...`;
                    }
                    
                    // Continue polling if within time limit
                    if (Date.now() - startTime < maxPollingTime) {
                        setTimeout(pollJobStatus, pollingInterval);
                    } else {
                        throw new Error('Processing timeout. Please try again later.');
                    }
                }
                
            } catch (error) {
                console.error('Error polling job status:', error);
                showToast(error.message || 'Failed to check processing status', 'error');
                summaryModal.style.display = 'none';
            }
        };
        
        // Start polling
        setTimeout(pollJobStatus, pollingInterval);
    }
    
    function displaySummary(summaryData) {
        // Update summary modal content
        summaryTitle.textContent = summaryData.title;
        summaryBody.innerHTML = markdownToHTML(summaryData.summary);
        
        // Add processing type indicator
        const processingType = summaryData.processing_type || 'standard';
        const typeIndicator = document.createElement('div');
        typeIndicator.className = 'processing-type-indicator';
        typeIndicator.innerHTML = `<small>Processing: ${processingType}</small>`;
        summaryTitle.appendChild(typeIndicator);
        
        // Hide loading spinner and show content
        summaryLoading.classList.add('hidden');
        summaryContent.classList.remove('hidden');
        
        // Clean up processing info if it exists
        const processingInfo = summaryLoading.querySelector('.processing-info');
        if (processingInfo) {
            processingInfo.remove();
        }
        
        // Reset loading text
        const loadingText = summaryLoading.querySelector('p');
        if (loadingText) {
            loadingText.textContent = 'Generating summary...';
        }
        
        // Reset video preview
        videoPreview.classList.add('hidden');
        youtubeUrlInput.value = '';
        currentVideo = null;
        
        // Show success message
        const processingTypeMsg = processingType === 'cached' ? 'from cache' : 
                                 processingType === 'fallback' ? 'using fallback method' : 
                                 processingType === 'async' ? 'asynchronously' : '';
        showToast(`Summary generated successfully ${processingTypeMsg}`, 'success');
    }
    
    async function fetchVideoSummary(videoId) {
        // Show modal with loading spinner
        summaryContent.classList.add('hidden');
        summaryLoading.classList.remove('hidden');
        summaryModal.style.display = 'block';
        
        try {
            const response = await fetch(`/api/video-details/${videoId}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to fetch video summary');
            }
            
            const data = await response.json();
            
            // Update summary modal content
            summaryTitle.textContent = data.title;
            summaryBody.innerHTML = markdownToHTML(data.summary);
            
            // Hide loading spinner and show content
            summaryLoading.classList.add('hidden');
            summaryContent.classList.remove('hidden');
            
        } catch (error) {
            console.error('Error:', error);
            closeModalHandler();
            showToast(error.message, 'error');
        }
    }
    
    async function updateUsageStats() {
        try {
            const response = await fetch('/api/user-usage');
            if (!response.ok) return;
            
            const data = await response.json();
            
            // Find the progress bar and update it
            const progressBar = document.querySelector('.progress-bar');
            if (progressBar) {
                // Ensure percentage_used exists and is a number
                const percentage = data.percentage_used !== undefined && !isNaN(data.percentage_used) ? 
                    data.percentage_used : 0;
                    
                // Apply the width style
                progressBar.style.width = `${percentage}%`;
                console.log('Setting progress bar width to:', `${percentage}%`);
            }
            
            // Update usage text
            const usageText = document.querySelector('.usage-meter p');
            if (usageText) {
                usageText.textContent = `${data.minutes_used || 0} / ${data.minutes_limit || 0} minutes used`;
            }
            
        } catch (error) {
            console.error('Error updating usage stats:', error);
        }
    }
    
    function closeModalHandler() {
        summaryModal.style.display = 'none';
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
    
    // Click outside modal to close
    window.addEventListener('click', function(event) {
        if (event.target === summaryModal) {
            closeModalHandler();
        }
    });
    
    // Convert markdown to HTML
    function markdownToHTML(markdown) {
        if (!markdown) return '';
        
        // Basic markdown conversion
        let html = markdown
            // Headers
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            
            // Lists
            .replace(/^\s*\d+\.\s+(.*$)/gm, '<li>$1</li>')
            .replace(/^\s*[\-\*]\s+(.*$)/gm, '<li>$1</li>')
            
            // Paragraphs
            .replace(/^([^\n<]*)\n/gm, '<p>$1</p>');
        
        // Wrap list items in <ul> or <ol>
        html = html.replace(/<li>.*?<\/li>/gs, match => {
            return '<ul>' + match + '</ul>';
        });
        
        return html;
    }
});
