// ===== VEXU ITICs MINIMAL Main JavaScript =====

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== MOBILE NAVIGATION =====
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
        
        // Close menu when clicking on a link
        const navLinks = document.querySelectorAll('.nav-menu a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!hamburger.contains(e.target) && !navMenu.contains(e.target)) {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            }
        });
    }
    
    // ===== SMOOTH SCROLLING =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offsetTop = target.offsetTop - 80; // Account for fixed header
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // ===== HEADER SCROLL EFFECT =====
    const header = document.querySelector('.header-minimal');
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;
        
        if (header) {
            // Add background blur when scrolled
            if (currentScrollY > 50) {
                header.style.background = 'rgba(255, 255, 255, 0.9)';
                header.style.backdropFilter = 'blur(16px)';
            } else {
                header.style.background = 'rgba(255, 255, 255, 0.8)';
                header.style.backdropFilter = 'blur(12px)';
            }
            
            // Hide/show header on scroll direction
            if (Math.abs(currentScrollY - lastScrollY) > 10) {
                if (currentScrollY > lastScrollY && currentScrollY > 100) {
                    // Scrolling down
                    header.style.transform = 'translateY(-100%)';
                } else {
                    // Scrolling up
                    header.style.transform = 'translateY(0)';
                }
                lastScrollY = currentScrollY;
            }
        }
    });
    
    // ===== DEVELOPER TABS =====
    const devTabs = document.querySelector('.dev-tabs-minimal');
    if (devTabs) {
        const tabButtons = devTabs.querySelectorAll('.tab-btn-minimal');
        const tabPanes = devTabs.querySelectorAll('.tab-pane-minimal');
        
        tabButtons.forEach((button, index) => {
            button.addEventListener('click', () => {
                // Remove active class from all buttons and panes
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabPanes.forEach(pane => pane.classList.remove('active'));
                
                // Add active class to clicked button and corresponding pane
                button.classList.add('active');
                if (tabPanes[index]) {
                    tabPanes[index].classList.add('active');
                }
            });
        });
    }
    
    // ===== COMPONENT CATEGORIES =====
    const componentCategories = document.querySelector('.component-categories-minimal');
    if (componentCategories) {
        const categoryButtons = componentCategories.querySelectorAll('.category-btn-minimal');
        const categoryPanes = componentCategories.querySelectorAll('.category-pane-minimal');
        
        categoryButtons.forEach((button, index) => {
            button.addEventListener('click', () => {
                // Remove active class from all buttons and panes
                categoryButtons.forEach(btn => btn.classList.remove('active'));
                categoryPanes.forEach(pane => pane.classList.remove('active'));
                
                // Add active class to clicked button and corresponding pane
                button.classList.add('active');
                if (categoryPanes[index]) {
                    categoryPanes[index].classList.add('active');
                }
            });
        });
    }
    
    // ===== FORM HANDLING =====
    const joinForm = document.getElementById('join-form');
    if (joinForm) {
        joinForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            // Simple validation
            if (!data.name || !data.email || !data.role) {
                showNotification('Por favor completa todos los campos requeridos.', 'error');
                return;
            }
            
            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email)) {
                showNotification('Por favor ingresa un email válido.', 'error');
                return;
            }
            
            // Success message
            showNotification('¡Gracias por tu interés! Te contactaremos pronto.', 'success');
            this.reset();
        });
    }
    
    // ===== NOTIFICATION SYSTEM =====
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" aria-label="Cerrar notificación">×</button>
        `;
        
        // Add styles
        Object.assign(notification.style, {
            position: 'fixed',
            top: '24px',
            right: '24px',
            padding: '16px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '500',
            zIndex: '10000',
            maxWidth: '400px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px',
            boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
            backgroundColor: type === 'success' ? '#059669' : '#dc2626',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        });
        
        notification.querySelector('button').style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);
        
        // Auto remove
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    // ===== SIMPLE FADE-IN ANIMATION ON SCROLL =====
    function handleScrollAnimations() {
        const animatedElements = document.querySelectorAll('.about-card-minimal, .code-card-minimal, .algorithm-card-minimal, .sensor-card-minimal, .strategy-card-minimal, .component-card-minimal');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
        
        animatedElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });
    }
    
    // ===== BUTTON RIPPLE EFFECT =====
    const buttons = document.querySelectorAll('.btn-minimal, .tab-btn-minimal, .category-btn-minimal');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            const ripple = document.createElement('span');
            ripple.style.cssText = `
                position: absolute;
                left: ${x}px;
                top: ${y}px;
                width: ${size}px;
                height: ${size}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                pointer-events: none;
                animation: ripple 0.6s ease-out;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
    
    // ===== ACCESSIBILITY IMPROVEMENTS =====
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        // ESC key to close mobile menu
        if (e.key === 'Escape') {
            hamburger?.classList.remove('active');
            navMenu?.classList.remove('active');
        }
        
        // Enter key on tab buttons
        if (e.key === 'Enter' && e.target.classList.contains('tab-btn-minimal')) {
            e.target.click();
        }
        
        if (e.key === 'Enter' && e.target.classList.contains('category-btn-minimal')) {
            e.target.click();
        }
    });
    
    // ===== INITIALIZE =====
    function initialize() {
        console.log('Initializing VEXU ITICs Minimal Website...');
        
        // Initialize scroll animations
        handleScrollAnimations();
        
        // Set first tab and category as active if none are active
        const firstTabBtn = document.querySelector('.tab-btn-minimal');
        const firstTabPane = document.querySelector('.tab-pane-minimal');
        if (firstTabBtn && !document.querySelector('.tab-btn-minimal.active')) {
            firstTabBtn.classList.add('active');
            if (firstTabPane) firstTabPane.classList.add('active');
        }
        
        const firstCategoryBtn = document.querySelector('.category-btn-minimal');
        const firstCategoryPane = document.querySelector('.category-pane-minimal');
        if (firstCategoryBtn && !document.querySelector('.category-btn-minimal.active')) {
            firstCategoryBtn.classList.add('active');
            if (firstCategoryPane) firstCategoryPane.classList.add('active');
        }
        
        console.log('VEXU ITICs website loaded successfully! 🤖✨');
    }
    
    // ===== SCROLL INDICATOR FUNCTIONALITY =====
    const scrollIndicator = document.querySelector('.scroll-indicator');
    if (scrollIndicator) {
        console.log('Scroll indicator found, setting up animation...');
        
        // Auto flip animation after 5 seconds
        setTimeout(function() {
            console.log('Adding flipped class after 5 seconds');
            scrollIndicator.classList.add('flipped');
        }, 5000);
        
        scrollIndicator.addEventListener('click', function() {
            const infoSection = document.querySelector('#info');
            if (infoSection) {
                infoSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
        
        // Hide scroll indicator when scrolling down
        window.addEventListener('scroll', function() {
            if (scrollIndicator) {
                const scrollPosition = window.scrollY;
                const windowHeight = window.innerHeight;
                
                if (scrollPosition > windowHeight * 0.3) {
                    scrollIndicator.style.opacity = '0';
                    scrollIndicator.style.transform = 'translateY(20px)';
                } else {
                    scrollIndicator.style.opacity = '1';
                    scrollIndicator.style.transform = 'translateY(0)';
                }
            }
        });
    } else {
        console.log('Scroll indicator NOT found');
    }
    
    // ===== NAVIGATION LINKS SMOOTH SCROLL =====
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // ===== CSS ANIMATIONS =====
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(2);
                opacity: 0;
            }
        }
        
        .notification {
            font-family: inherit;
        }
        
        /* Focus styles for accessibility */
        .tab-btn-minimal:focus,
        .category-btn-minimal:focus,
        .btn-minimal:focus {
            outline: 2px solid var(--primary-color);
            outline-offset: 2px;
        }
        
        /* Smooth transitions */
        .header-minimal {
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                        background 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                        backdrop-filter 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
    `;
    document.head.appendChild(style);
    
    // Initialize everything
    initialize();
    
    // ===== FLOATING MUSIC BUTTON FUNCTIONALITY =====
    const musicBtn = document.getElementById('musicBtn');
    const vexMusic = document.getElementById('vexMusic');
    let isPlaying = false;

    if (musicBtn && vexMusic) {
        // Set initial volume low
        vexMusic.volume = 0.3;

        musicBtn.addEventListener('click', function() {
            if (isPlaying) {
                // Stop music
                vexMusic.pause();
                vexMusic.currentTime = 0; // Reset to beginning
                musicBtn.classList.remove('playing');
                isPlaying = false;
            } else {
                // Try to play real audio first
                const playPromise = vexMusic.play();
                
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        musicBtn.classList.add('playing');
                        isPlaying = true;
                        console.log('Playing VEX audio file');
                    }).catch(error => {
                        console.log('Error playing audio file:', error);
                        console.log('Falling back to synthetic audio...');
                        createSimpleBeep();
                    });
                } else {
                    // Fallback for older browsers
                    try {
                        vexMusic.play();
                        musicBtn.classList.add('playing');
                        isPlaying = true;
                    } catch (error) {
                        console.log('Fallback to synthetic audio');
                        createSimpleBeep();
                    }
                }
            }
        });

        // Handle audio events
        vexMusic.addEventListener('ended', function() {
            // This shouldn't trigger since we're using loop, but just in case
            musicBtn.classList.remove('playing');
            isPlaying = false;
            console.log('Audio ended');
        });

        vexMusic.addEventListener('pause', function() {
            musicBtn.classList.remove('playing');
            isPlaying = false;
            console.log('Audio paused');
        });

        vexMusic.addEventListener('play', function() {
            musicBtn.classList.add('playing');
            isPlaying = true;
            console.log('Audio playing');
        });

        vexMusic.addEventListener('error', function(e) {
            console.log('Audio error:', e);
            musicBtn.classList.remove('playing');
            isPlaying = false;
        });

        // Check if audio can be played
        vexMusic.addEventListener('canplay', function() {
            console.log('VEX audio ready to play');
        });

        vexMusic.addEventListener('loadstart', function() {
            console.log('Loading VEX audio...');
        });

        // Fallback sound function
        function createSimpleBeep() {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                
                // Create a more complex robotic/VEX-style sound
                function playTechSound() {
                    const oscillator1 = audioContext.createOscillator();
                    const oscillator2 = audioContext.createOscillator();
                    const gainNode = audioContext.createGain();
                    const filterNode = audioContext.createBiquadFilter();
                    
                    oscillator1.connect(filterNode);
                    oscillator2.connect(filterNode);
                    filterNode.connect(gainNode);
                    gainNode.connect(audioContext.destination);
                    
                    // Set up filter for robotic sound
                    filterNode.type = 'lowpass';
                    filterNode.frequency.setValueAtTime(1000, audioContext.currentTime);
                    
                    // Main melody line
                    oscillator1.frequency.setValueAtTime(440, audioContext.currentTime); // A
                    oscillator1.frequency.setValueAtTime(523, audioContext.currentTime + 0.2); // C
                    oscillator1.frequency.setValueAtTime(659, audioContext.currentTime + 0.4); // E
                    oscillator1.frequency.setValueAtTime(784, audioContext.currentTime + 0.6); // G
                    
                    // Harmony line
                    oscillator2.frequency.setValueAtTime(220, audioContext.currentTime); // A octave lower
                    oscillator2.frequency.setValueAtTime(261, audioContext.currentTime + 0.2); // C octave lower
                    oscillator2.frequency.setValueAtTime(329, audioContext.currentTime + 0.4); // E octave lower
                    oscillator2.frequency.setValueAtTime(392, audioContext.currentTime + 0.6); // G octave lower
                    
                    // Set waveforms for robotic sound
                    oscillator1.type = 'square';
                    oscillator2.type = 'sawtooth';
                    
                    // Volume envelope
                    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
                    gainNode.gain.linearRampToValueAtTime(0.1, audioContext.currentTime + 0.05);
                    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime + 0.7);
                    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1.0);
                    
                    oscillator1.start();
                    oscillator2.start();
                    oscillator1.stop(audioContext.currentTime + 1.0);
                    oscillator2.stop(audioContext.currentTime + 1.0);
                }
                
                playTechSound();
                musicBtn.classList.add('playing');
                
                // Play the sound every 2 seconds while "playing"
                const intervalId = setInterval(() => {
                    if (musicBtn.classList.contains('playing')) {
                        playTechSound();
                    } else {
                        clearInterval(intervalId);
                    }
                }, 2000);
                
                // Stop after 10 seconds if still playing
                setTimeout(() => {
                    musicBtn.classList.remove('playing');
                    clearInterval(intervalId);
                }, 10000);
                
            } catch (e) {
                console.log('Audio not supported');
                // Visual feedback only
                musicBtn.classList.add('playing');
                setTimeout(() => {
                    musicBtn.classList.remove('playing');
                }, 2000);
            }
        }
    }
    
});