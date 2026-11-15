/**
 * QuizInsight - Collapsible Sidebar Dashboard Controller
 * Handles desktop collapse/expand with localStorage persistence,
 * Bootstrap 5 tooltips on collapsed menu icons,
 * and responsive mobile slide-out drawer behavior.
 */

(function () {
    'use strict';

    let tooltipInstances = [];

    function initTooltips(enable) {
        // Dispose existing tooltips
        tooltipInstances.forEach(function (t) {
            try { t.dispose(); } catch (e) { }
        });
        tooltipInstances = [];

        // Enable tooltips only when sidebar is collapsed on desktop
        if (enable && window.bootstrap && typeof window.bootstrap.Tooltip === 'function') {
            const links = document.querySelectorAll('.dashboard-sidebar.collapsed .sidebar-link[data-bs-toggle="tooltip"]');
            links.forEach(function (el) {
                try {
                    const tip = new window.bootstrap.Tooltip(el, {
                        placement: 'right',
                        trigger: 'hover',
                        boundary: 'window'
                    });
                    tooltipInstances.push(tip);
                } catch (e) { }
            });
        }
    }

    function isDesktop() {
        return window.innerWidth >= 992;
    }

    function setDesktopState(collapsed) {
        const sidebar = document.getElementById('dashboardSidebar');
        const main = document.getElementById('dashboardMain');
        if (!sidebar || !main) return;

        if (collapsed) {
            sidebar.classList.add('collapsed');
            main.classList.add('expanded');
            try { localStorage.setItem('quizinsight_sidebar_collapsed', 'true'); } catch (e) { }
            initTooltips(true);
        } else {
            sidebar.classList.remove('collapsed');
            main.classList.remove('expanded');
            try { localStorage.setItem('quizinsight_sidebar_collapsed', 'false'); } catch (e) { }
            initTooltips(false);
        }
    }

    function openMobileSidebar() {
        const sidebar = document.getElementById('dashboardSidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        if (sidebar) sidebar.classList.add('mobile-open');
        if (backdrop) backdrop.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
        const sidebar = document.getElementById('dashboardSidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        if (sidebar) sidebar.classList.remove('mobile-open');
        if (backdrop) backdrop.classList.remove('show');
        document.body.style.overflow = '';
    }

    function toggleSidebar() {
        if (isDesktop()) {
            const sidebar = document.getElementById('dashboardSidebar');
            const isCurrentlyCollapsed = sidebar && sidebar.classList.contains('collapsed');
            setDesktopState(!isCurrentlyCollapsed);
        } else {
            const sidebar = document.getElementById('dashboardSidebar');
            if (sidebar && sidebar.classList.contains('mobile-open')) {
                closeMobileSidebar();
            } else {
                openMobileSidebar();
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const toggleBtn = document.getElementById('sidebarToggleBtn');
        const mobileCloseBtn = document.getElementById('sidebarMobileClose');
        const backdrop = document.getElementById('sidebarBackdrop');
        const sidebar = document.getElementById('dashboardSidebar');

        // Restore saved desktop state
        if (isDesktop()) {
            let savedState = 'false';
            try { savedState = localStorage.getItem('quizinsight_sidebar_collapsed'); } catch (e) { }
            if (savedState === 'true') {
                setDesktopState(true);
            } else {
                setDesktopState(false);
            }
        }

        // Toggle button click (hamburger)
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function (e) {
                e.preventDefault();
                toggleSidebar();
            });
        }

        // Mobile close button
        if (mobileCloseBtn) {
            mobileCloseBtn.addEventListener('click', function (e) {
                e.preventDefault();
                closeMobileSidebar();
            });
        }

        // Backdrop click to close mobile drawer
        if (backdrop) {
            backdrop.addEventListener('click', function () {
                closeMobileSidebar();
            });
        }

        // Auto close mobile drawer when a sidebar navigation link is clicked
        if (sidebar) {
            const navLinks = sidebar.querySelectorAll('.sidebar-link');
            navLinks.forEach(function (link) {
                link.addEventListener('click', function () {
                    if (!isDesktop()) {
                        closeMobileSidebar();
                    }
                });
            });
        }

        // Handle window resizing
        window.addEventListener('resize', function () {
            if (isDesktop()) {
                closeMobileSidebar();
                let saved = 'false';
                try { saved = localStorage.getItem('quizinsight_sidebar_collapsed'); } catch (e) { }
                setDesktopState(saved === 'true');
            } else {
                initTooltips(false);
                if (sidebar) sidebar.classList.remove('collapsed');
                const main = document.getElementById('dashboardMain');
                if (main) main.classList.remove('expanded');
            }
        });
    });
})();
