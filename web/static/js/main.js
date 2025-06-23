/**
 * Main JavaScript for the Blog Search Engine
 */

document.addEventListener('DOMContentLoaded', function() {
    // Focus on search input when page loads
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.focus();
    }
    
    // Add event listener for search form
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const query = searchInput.value.trim();
            if (!query) {
                e.preventDefault();
                searchInput.focus();
            } else {
                // Save search to history
                saveSearchToHistory(query);
            }
        });
    }
    
    // Add event listeners for result items to track clicks
    const resultLinks = document.querySelectorAll('.result-item h2 a');
    resultLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Track click analytics if needed
            console.log('Clicked result:', this.href);
        });
    });
    
    // Add animation to search results
    const resultItems = document.querySelectorAll('.result-item');
    if (resultItems.length > 0) {
        resultItems.forEach((item, index) => {
            // Add a slight delay to each item for a cascading effect
            setTimeout(() => {
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            }, 100 * index);
        });
    }
    
    // Search history functionality
    const historyToggle = document.querySelector('.history-toggle');
    const searchHistory = document.querySelector('.search-history');
    
    if (historyToggle && searchHistory) {
        historyToggle.addEventListener('click', function() {
            const isVisible = searchHistory.style.display === 'block';
            searchHistory.style.display = isVisible ? 'none' : 'block';
            
            // Toggle icon
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-chevron-down');
                icon.classList.toggle('fa-chevron-up');
            }
        });
        
        // Load and display search history
        displaySearchHistory();
        
        // Clear history button
        const clearHistoryBtn = document.getElementById('clear-history');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', function() {
                localStorage.removeItem('searchHistory');
                displaySearchHistory();
            });
        }
    }
}); 

/**
 * Save search query to local storage history
 */
function saveSearchToHistory(query) {
    // Get existing history or initialize new array
    let history = JSON.parse(localStorage.getItem('searchHistory')) || [];
    
    // Remove duplicate if exists
    history = history.filter(item => item.query !== query);
    
    // Add new search to beginning
    history.unshift({
        query: query,
        timestamp: new Date().toISOString()
    });
    
    // Keep only last 10 searches
    if (history.length > 10) {
        history = history.slice(0, 10);
    }
    
    // Save back to localStorage
    localStorage.setItem('searchHistory', JSON.stringify(history));
}

/**
 * Display search history from local storage
 */
function displaySearchHistory() {
    const historyList = document.getElementById('search-history-list');
    if (!historyList) return;
    
    // Clear current list
    historyList.innerHTML = '';
    
    // Get history from localStorage
    const history = JSON.parse(localStorage.getItem('searchHistory')) || [];
    
    if (history.length === 0) {
        const emptyItem = document.createElement('li');
        emptyItem.textContent = 'No search history yet';
        historyList.appendChild(emptyItem);
        return;
    }
    
    // Add each search to the list
    history.forEach(item => {
        const listItem = document.createElement('li');
        
        const link = document.createElement('a');
        link.href = `/search?q=${encodeURIComponent(item.query)}`;
        link.textContent = item.query;
        
        const timestamp = document.createElement('span');
        timestamp.textContent = formatDate(new Date(item.timestamp));
        timestamp.className = 'search-time';
        
        listItem.appendChild(link);
        listItem.appendChild(timestamp);
        historyList.appendChild(listItem);
    });
}

/**
 * Format date to readable string
 */
function formatDate(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.round(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hr ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} day ago`;
    
    return date.toLocaleDateString();
} 