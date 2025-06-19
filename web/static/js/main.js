/**
 * Main JavaScript for the Google Blog Search Engine
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
            }
        });
    }
    
    // Add event listeners for result items to track clicks
    const resultLinks = document.querySelectorAll('.result-item h2 a');
    resultLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Track click analytics if needed
            console.log('Clicked result:', this.href);
            
            // Open in new tab (already handled by target="_blank")
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
}); 