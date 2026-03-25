import pygame
import sys

# Инициализация Pygame
pygame.init()

# Настройки окна
WIDTH = 400
HEIGHT = 200
WINDOW = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("HP and SHD Bars")

# Цвета
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
WHITE = (255, 255, 255)

# Значения HP и SHD
MAX_HP = 12
MAX_SHD = 2
current_hp = MAX_HP
current_shd = MAX_SHD

# Шрифт
font = pygame.font.Font(None, 36)

# Основной цикл
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:  # Уменьшить HP (нажатие H)
                current_hp = max(0, current_hp - 1)
            elif event.key == pygame.K_s:  # Уменьшить SHD (нажатие S)
                current_shd = max(0, current_shd - 1)

    # Очистка экрана
    WINDOW.fill(BLACK)

    # Отрисовка полоски HP
    hp_text = font.render(f"HP: {current_hp}/{MAX_HP}", True, WHITE)
    hp_rect = hp_text.get_rect(topleft=(10, 10))
    WINDOW.blit(hp_text, hp_rect)
    pygame.draw.rect(WINDOW, GREEN, (10, 50, (current_hp / MAX_HP) * 200, 20))

    # Отрисовка полоски SHD
    shd_text = font.render(f"SHD: {current_shd}/{MAX_SHD}", True, WHITE)
    shd_rect = shd_text.get_rect(topleft=(10, 80))
    WINDOW.blit(shd_text, shd_rect)
    pygame.draw.rect(WINDOW, BLUE, (10, 120, (current_shd / MAX_SHD) * 200, 20))

    # Обновление экрана
    pygame.display.flip()
    clock.tick(60)

# Завершение
pygame.quit()
sys.exit()