// My Videos page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const viewSummaryButtons = document.querySelectorAll('.view-summary-btn');
    const summaryModal = document.getElementById('summary-modal');
    const closeModal = document.querySelector('.close-modal');
    const summaryTitle = document.getElementById('summary-title');
    const summaryBody = document.getElementById('summary-body');
    const downloadBtn = document.getElementById('download-notes-btn');
    const toast = document.getElementById('toast');
    
    // Event listeners
    viewSummaryButtons.forEach(button => {
        button.addEventListener('click', function() {
            const videoId = this.getAttribute('data-video-id');
            fetchVideoSummary(videoId);
        });
    });
    
    closeModal.addEventListener('click', function() {
        summaryModal.style.display = 'none';
    });
    
    // Click outside modal to close
    window.addEventListener('click', function(event) {
        if (event.target === summaryModal) {
            summaryModal.style.display = 'none';
        }
    });
    
    // Download notes button
    downloadBtn.addEventListener('click', function() {
        downloadNotes();
    });
    
    // Functions
    async function fetchVideoSummary(videoId) {
        try {
            // Show loading state
            summaryBody.innerHTML = '<div class="loading">Loading summary...</div>';
            summaryModal.style.display = 'block';
            
            const response = await fetch(`/api/video-details/${videoId}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to fetch video summary');
            }
            
            const data = await response.json();
            
            // Update summary modal content
            summaryTitle.textContent = data.title;
            summaryBody.innerHTML = markdownToHTML(data.summary);
            
            // Store current note data for download
            summaryModal.dataset.videoTitle = data.title;
            summaryModal.dataset.notesContent = data.summary;
            
        } catch (error) {
            console.error('Error:', error);
            summaryBody.innerHTML = `<div class="error">Error: ${error.message}</div>`;
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
    
        // Download notes as text file
    function downloadNotes() {
        try {
            const title = summaryModal.dataset.videoTitle || 'Video Notes';
            const content = summaryModal.dataset.notesContent || '';
            
            if (!content) {
                showToast('No content available to download', 'error');
                return;
            }
            
            // Create a blob with the notes content
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            // Create temporary link and trigger download
            const a = document.createElement('a');
            a.href = url;
            a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_notes.txt`;
            document.body.appendChild(a);
            a.click();
            
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('Notes downloaded successfully', 'success');
        } catch (error) {
            console.error('Download error:', error);
            showToast('Error downloading notes', 'error');
        }
    }
    
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
