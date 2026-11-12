/**
 * NovaAI - Theme Controller (Dark/Light Mode)
 */

(function () {
    const THEME_KEY = 'nova_theme';

    function getPreferredTheme() {
        const storedTheme = localStorage.getItem(THEME_KEY);
        if (storedTheme) {
            return storedTheme;
        }
        return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);

        // Update any label text if present
        const label = document.getElementById('theme-toggle-label');
        if (label) {
            label.textContent = theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
        }
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }

    // Initialize Theme immediately
    applyTheme(getPreferredTheme());

    // Bind theme toggle buttons on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
        const toggleButtons = document.querySelectorAll('#theme-toggle-btn, #top-theme-btn, #theme-toggle-menu-btn');
        toggleButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleTheme();
            });
        });
    });

    // Expose global methods
    window.toggleTheme = toggleTheme;
    window.setTheme = applyTheme;
})();

