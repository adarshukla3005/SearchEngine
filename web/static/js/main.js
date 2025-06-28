/**
 * Main JavaScript for the Personal Blog Search Engine
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Search engine script loaded');
    
    // Focus on search input when page loads
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.focus();
        console.log('Search input focused');
    }
    
    // Add event listener for search form
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const query = searchInput.value.trim();
            if (!query) {
                e.preventDefault();
                searchInput.focus();
                console.log('Empty search prevented');
            } else {
                console.log('Searching for:', query);
            }
        });
    }
    
    // Add event listeners for result items to track clicks
    const resultLinks = document.querySelectorAll('.result-item h2 a, .search-result h3 a');
    resultLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Track click analytics if needed
            console.log('Clicked result:', this.href);
            
            // Open in new tab (already handled by target="_blank")
        });
    });
}); 