// Configuración del carrusel
const slides = document.querySelector('.slides');
const slideItems = document.querySelectorAll('.slide');
let currentIndex = 0;
const intervalTime = 6000;

// Efecto de partículas
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

function nextSlide() {
    slideItems[currentIndex].classList.remove('active');
    currentIndex = (currentIndex + 1) % slideItems.length;
    slideItems[currentIndex].classList.add('active');
    
    slideItems.forEach((slide, index) => {
        const offset = (index - currentIndex) * 100;
        const scale = index === currentIndex ? 1 : 0.9;
        const opacity = index === currentIndex ? 1 : 0.7;
        const zIndex = index === currentIndex ? 1 : 0;
        
        slide.style.transform = `translateX(${offset}%) scale(${scale})`;
        slide.style.opacity = opacity;
        slide.style.zIndex = zIndex;
    });
}

document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    setInterval(nextSlide, intervalTime);
    
    // Configuración inicial
    slideItems.forEach((slide, index) => {
        const offset = (index - currentIndex) * 100;
        const scale = index === currentIndex ? 1 : 0.9;
        const opacity = index === currentIndex ? 1 : 0.7;
        const zIndex = index === currentIndex ? 1 : 0;
        
        slide.style.transform = `translateX(${offset}%) scale(${scale})`;
        slide.style.opacity = opacity;
        slide.style.zIndex = zIndex;
    });
});