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

    // Theme switching functionality
    const themeToggle = document.getElementById('theme-toggle');
    
    // Check for saved theme preference or use system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Set initial theme based on saved preference or system preference
    if (savedTheme === 'dark' || (!savedTheme && prefersDarkScheme.matches)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (themeToggle) themeToggle.checked = true;
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        if (themeToggle) themeToggle.checked = false;
    }
    
    // Listen for toggle changes
    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                console.log('Dark mode enabled');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                console.log('Light mode enabled');
            }
        });
    }
    
    // Listen for system preference changes
    prefersDarkScheme.addEventListener('change', function(e) {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                if (themeToggle) themeToggle.checked = true;
                console.log('System switched to dark mode');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                if (themeToggle) themeToggle.checked = false;
                console.log('System switched to light mode');
            }
        }
    });
}); 