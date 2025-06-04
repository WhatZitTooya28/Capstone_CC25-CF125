// File: frontend/src/js/index.js

import '../styles/styles.css'; 

console.log("TrashGu Frontend Started from src/js/index.js!");

// --- Fungsi untuk Update Tampilan Navbar Berdasarkan Status Login ---
function updateNavbarBasedOnLoginStatus() {
    const authToken = localStorage.getItem('authToken');
    const currentUserString = localStorage.getItem('currentUser');
    let currentUser = null;
    if (currentUserString) {
        try {
            currentUser = JSON.parse(currentUserString);
        } catch (e) {
            console.error("Error parsing currentUser from localStorage:", e);
            localStorage.removeItem('authToken'); 
            localStorage.removeItem('currentUser');
        }
    }

    // Elemen Navbar Desktop
    const navAuthGuest = document.getElementById('nav-auth-guest');
    const navAuthUser = document.getElementById('nav-auth-user'); // Ini adalah kontainer dropdown
    const userProfileButton = document.getElementById('user-profile-button');
    const navbarUserNameShort = document.getElementById('navbar-user-name-short');
    const dropdownUserNameFull = document.getElementById('dropdown-user-name-full');
    const navbarUserAvatar = document.getElementById('navbar-user-avatar'); // Untuk avatar
    const navbarLogoutButton = document.getElementById('navbar-logout-button'); // Logout di dropdown
    const userProfileDropdown = document.getElementById('user-profile-dropdown');

    // Elemen Navbar Mobile
    const mobileNavAuthGuest = document.getElementById('mobile-nav-auth-guest');
    const mobileNavAuthUser = document.getElementById('mobile-nav-auth-user');
    const mobileNavbarUserName = document.getElementById('mobile-navbar-user-name');
    const mobileNavbarLogoutButton = document.getElementById('mobile-navbar-logout-button');
    const mobileNavProfileLink = document.getElementById('mobile-nav-profile-link'); // Tautan profil di mobile
    const mobileNavDashboardLink = document.querySelector('#mobile-menu a[href="./dashboard.html"]'); // Tautan dashboard di mobile


    if (authToken && currentUser) {
        // Pengguna sudah login
        if (navAuthGuest) navAuthGuest.classList.add('hidden');
        if (navAuthUser) navAuthUser.classList.remove('hidden');
        
        const displayName = currentUser.namaPengguna || (currentUser.email ? currentUser.email.split('@')[0] : 'User');
        if (navbarUserNameShort) navbarUserNameShort.textContent = displayName;
        if (dropdownUserNameFull) dropdownUserNameFull.textContent = displayName;
        // TODO: Update avatar jika ada URL avatar di currentUser
        // if (navbarUserAvatar && currentUser.avatarUrl) navbarUserAvatar.src = currentUser.avatarUrl;

        if (mobileNavAuthGuest) mobileNavAuthGuest.classList.add('hidden');
        if (mobileNavAuthUser) mobileNavAuthUser.classList.remove('hidden');
        if (mobileNavbarUserName) mobileNavbarUserName.textContent = displayName;
        if (mobileNavProfileLink) mobileNavProfileLink.classList.remove('hidden');
        if (mobileNavDashboardLink) mobileNavDashboardLink.classList.remove('hidden');


        const setupLogout = (button) => {
            if (button) {
                // Hapus event listener lama jika ada, untuk menghindari multiple listener
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);
                newButton.addEventListener('click', function (event) {
                    event.preventDefault();
                    localStorage.removeItem('authToken');
                    localStorage.removeItem('currentUser');
                    window.location.href = '/login.html'; 
                });
            }
        };
        setupLogout(navbarLogoutButton);
        setupLogout(mobileNavbarLogoutButton);

        // Logika untuk toggle dropdown profil di desktop
        if (userProfileButton && userProfileDropdown) {
            userProfileButton.addEventListener('click', (event) => {
                event.stopPropagation();
                userProfileDropdown.classList.toggle('hidden');
            });
            // Klik di luar dropdown untuk menutupnya
            document.addEventListener('click', (event) => {
                if (!userProfileButton.contains(event.target) && !userProfileDropdown.contains(event.target)) {
                    userProfileDropdown.classList.add('hidden');
                }
            });
        }

    } else {
        // Pengguna belum login
        if (navAuthGuest) navAuthGuest.classList.remove('hidden');
        if (navAuthUser) navAuthUser.classList.add('hidden');

        if (mobileNavAuthGuest) mobileNavAuthGuest.classList.remove('hidden');
        if (mobileNavAuthUser) mobileNavAuthUser.classList.add('hidden');
        if (mobileNavProfileLink) mobileNavProfileLink.classList.add('hidden');
        if (mobileNavDashboardLink) mobileNavDashboardLink.classList.add('hidden');
    }
}

// --- Fungsi untuk Menandai Tautan Navbar Aktif ---
function setActiveNavLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html'; // Default ke index.html jika path kosong
    const navLinksDesktop = {
        'index.html': document.getElementById('nav-beranda'),
        'klasifikasi.html': document.getElementById('nav-klasifikasi'),
        'tim-teknologi.html': document.getElementById('nav-tim-teknologi'),
        // Tambahkan ID untuk link Artikel jika ada di HTML
        // 'artikel.html': document.getElementById('nav-artikel'), 
    };
    const navLinksMobile = {
        'index.html': document.querySelector('#mobile-menu .mobile-nav-beranda'),
        'klasifikasi.html': document.querySelector('#mobile-menu .mobile-nav-klasifikasi'),
        'tim-teknologi.html': document.querySelector('#mobile-menu .mobile-nav-tim-teknologi'),
    };

    const resetStyles = (links) => {
        Object.values(links).forEach(link => {
            if (link) {
                link.classList.remove('text-[#3F7D58]', 'font-semibold');
                link.classList.add('text-gray-600');
            }
        });
    };

    resetStyles(navLinksDesktop);
    resetStyles(navLinksMobile);

    if (navLinksDesktop[currentPage]) {
        navLinksDesktop[currentPage].classList.add('text-[#3F7D58]', 'font-semibold');
        navLinksDesktop[currentPage].classList.remove('text-gray-600');
    }
     if (navLinksMobile[currentPage]) {
        navLinksMobile[currentPage].classList.add('text-[#3F7D58]', 'font-semibold');
        navLinksMobile[currentPage].classList.remove('text-gray-600');
    }
}


// --- Event Listener Global ---
document.addEventListener('DOMContentLoaded', function () {
    updateNavbarBasedOnLoginStatus();
    setActiveNavLink();

    const mobileMenuButton = document.getElementById('mobile-menu-button') || 
                             document.getElementById('mobile-menu-button-tim') || 
                             document.getElementById('mobile-menu-button-klasifikasi') ||
                             document.getElementById('mobile-menu-button-hasil'); 
    const mobileMenu = document.getElementById('mobile-menu') || 
                       document.getElementById('mobile-menu-tim') ||
                       document.getElementById('mobile-menu-klasifikasi') ||
                       document.getElementById('mobile-menu-hasil');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }

    const scrollToTopBtn = document.getElementById('scrollToTopBtn') || 
                           document.getElementById('scrollToTopBtnTimPage') || 
                           document.getElementById('scrollToTopBtnKlasifikasi') ||
                           document.getElementById('scrollToTopBtnHasil') ||
                           document.getElementById('scrollToTopBtnDashboard');
                           
    if (scrollToTopBtn) {
        const mainScrollArea = document.querySelector('main.flex-1.overflow-y-auto');
        const scrollElement = mainScrollArea || window;

        const handleScroll = () => {
            const scrollTop = mainScrollArea ? mainScrollArea.scrollTop : (document.documentElement.scrollTop || document.body.scrollTop);
            if (scrollTop > 300) {
                scrollToTopBtn.classList.remove('hidden', 'opacity-0', 'visibility-hidden');
                scrollToTopBtn.classList.add('opacity-100', 'visibility-visible');
            } else {
                scrollToTopBtn.classList.remove('opacity-100', 'visibility-visible');
                scrollToTopBtn.classList.add('hidden', 'opacity-0', 'visibility-hidden');
            }
        };
        scrollElement.addEventListener('scroll', handleScroll);
        
        scrollToTopBtn.addEventListener('click', () => {
            scrollElement.scrollTo({top: 0, behavior: 'smooth'});
        });
    }
});
