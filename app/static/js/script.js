document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    initAutoAdvance();
});

// Función de partículas (mantener igual)
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        
        const size = Math.random() * 5 + 1;
        const posX = Math.random() * 100;
        const posY = Math.random() * 100;
        const delay = Math.random() * 5;
        const duration = Math.random() * 10 + 10;
        
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.left = `${posX}%`;
        particle.style.top = `${posY}%`;
        particle.style.opacity = Math.random() * 0.5 + 0.1;
        particle.style.animation = `float ${duration}s ease-in-out ${delay}s infinite`;
        
        particlesContainer.appendChild(particle);
    }
}

function initAutoAdvance() {
    const slides = document.querySelectorAll('.slide');
    const slideCount = slides.length;
    let currentIndex = 0;
    const intervalTime = 10000; // 10 segundos por slide
    
    if (slideCount <= 1) return; // No necesita avanzar si hay solo 1 slide

    function showSlide(index) {
        // Oculta todos los slides
        slides.forEach(slide => {
            slide.classList.remove('active');
            slide.style.opacity = '0';
        });
        
        // Muestra el slide actual
        slides[index].classList.add('active');
        slides[index].style.opacity = '1';
        currentIndex = index;
    }

    function nextSlide() {
        const newIndex = (currentIndex + 1) % slideCount;
        showSlide(newIndex);
    }

    // Iniciar el avance automático
    showSlide(0);
    setInterval(nextSlide, intervalTime);
}