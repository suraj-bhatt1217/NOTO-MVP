// Dashboard functionality for YouTube video summarization
document.addEventListener('DOMContentLoaded', function() {
  // Initialize progress bars based on data-progress attributes
  const progressBars = document.querySelectorAll('.progress-bar[data-progress]');
  progressBars.forEach(bar => {
    const progress = parseFloat(bar.getAttribute('data-progress'));
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
                    video_url: youtubeUrlInput.value.trim() 
                }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate summary');
            }
            
            const data = await response.json();
            
            // Update summary modal content
            summaryTitle.textContent = data.title;
            summaryBody.innerHTML = markdownToHTML(data.summary);
            
            // Hide loading spinner and show content
            summaryLoading.classList.add('hidden');
            summaryContent.classList.remove('hidden');
            
            // Reset video preview
            videoPreview.classList.add('hidden');
            youtubeUrlInput.value = '';
            currentVideo = null;
            
            // Update the usage stats (could fetch fresh data or use DOM manipulation)
            updateUsageStats();
            
        } catch (error) {
            console.error('Error:', error);
            closeModalHandler();
            showToast(error.message, 'error');
        }
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
                progressBar.style.width = `${data.percentage_used}%`;
            }
            
            // Update usage text
            const usageText = document.querySelector('.usage-meter p');
            if (usageText) {
                usageText.textContent = `${data.minutes_used} / ${data.minutes_limit} minutes used`;
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
