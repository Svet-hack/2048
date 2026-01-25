import os
import json
import random
import arcade

WINDOW_WIDTH = 720
WINDOW_HEIGHT = 720
WINDOW_TITLE = "2048 Adaptive Grid"

FIELD_SCALE = 0.8  # 80% окна занимает поле
GRID_SIZE = 4      # менять на 4,5,6 и т.д.
CELL_PADDING = 6   # отступ между клетками (в пикселях)

# Цвета (RGB)
BACKGROUND_COLOR = (187, 173, 160)
TILE_COLORS = {
    0: (205, 193, 180),
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}

BOX_COLOR = (119, 110, 101)  # цвет для Score и BestScore
TEXT_COLOR_LIGHT = arcade.color.WHITE
TEXT_COLOR_DARK = arcade.color.BLACK

print(os.path.expanduser("~"))
BEST_SCORE_FILE = os.path.join(os.path.expanduser("~"), ".2048_best_score.json")


class Game2048(arcade.Window):
    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
        arcade.set_background_color(BACKGROUND_COLOR)

        # Параметры поля и клетки
        self.field_pixel_size = int(min(WINDOW_WIDTH, WINDOW_HEIGHT) * FIELD_SCALE)
        self.cell_size = self.field_pixel_size / GRID_SIZE
        self.field_offset_x = (WINDOW_WIDTH - self.field_pixel_size) / 2
        self.field_offset_y = (WINDOW_HEIGHT - self.field_pixel_size) / 2

        # Игровая сетка (список списков)
        self.grid = self.create_empty_grid(GRID_SIZE)

        # Счёт
        self.score = 0
        self.best_score = self.load_best_score()
        self.game_over = False
        self.win = False

        # Поместить две стартовые плитки "2"
        self.spawn_initial_tiles(2)

    def load_best_score(self):
        try:
            with open(BEST_SCORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("best_score", 0))
        except Exception:
            return 0

    def save_best_score(self):
        try:
            with open(BEST_SCORE_FILE, "w", encoding="utf-8") as f:
                json.dump({"best_score": int(self.best_score)}, f)
        except Exception:
            pass

    def create_empty_grid(self, n):
        """Создать n x n сетку заполненную нулями."""
        return [[0 for _ in range(n)] for _ in range(n)]

    def spawn_initial_tiles(self, count=2):
        """Заполнить count случайных пустых ячеек значением 2."""
        n = GRID_SIZE * GRID_SIZE
        count = min(count, n)
        indices = random.sample(range(n), k=count)
        for idx in indices:
            row = idx // GRID_SIZE
            col = idx % GRID_SIZE
            self.grid[row][col] = 2

    def spawn_one_tile(self):
        empty = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.grid[r][c] == 0]
        if not empty:
            return
        r, c = random.choice(empty)
        self.grid[r][c] = 4 if random.random() < 0.1 else 2

    # ----------------------
    # Логика сжатия + слияния
    # ----------------------
    @staticmethod
    def compress_list_left(line):
        """Вернуть список, где все ненулевые элементы сжаты влево в том же порядке, остальные - нули."""
        nonzeros = [x for x in line if x != 0]
        return nonzeros + [0] * (len(line) - len(nonzeros))

    @staticmethod
    def merge_list_left(line):
        """Выполнить сжатие и слияние по правилам 2048 слева направо.

        Возвращает (new_line, score_gained).
        """
        nonzeros = [x for x in line if x != 0]
        merged = []
        score_gained = 0
        i = 0
        while i < len(nonzeros):
            if i + 1 < len(nonzeros) and nonzeros[i] == nonzeros[i + 1]:
                new_val = nonzeros[i] * 2
                merged.append(new_val)
                score_gained += new_val
                i += 2
            else:
                merged.append(nonzeros[i])
                i += 1
        merged += [0] * (len(line) - len(merged))
        return merged, score_gained

    def move_left(self):
        changed = False
        gained_total = 0
        for r in range(GRID_SIZE):
            old = list(self.grid[r])
            new, gained = self.merge_list_left(old)
            if new != old:
                changed = True
                self.grid[r] = new
                gained_total += gained
        if gained_total:
            self.score += gained_total
        return changed

    def move_right(self):
        changed = False
        gained_total = 0
        for r in range(GRID_SIZE):
            old = list(self.grid[r])
            rev = list(reversed(old))
            new_rev, gained = self.merge_list_left(rev)
            new = list(reversed(new_rev))
            if new != old:
                changed = True
                self.grid[r] = new
                gained_total += gained
        if gained_total:
            self.score += gained_total
        return changed

    def move_up(self):
        """
        Переместить плитки вверх (в сторону увеличения индекса row).
        grid хранится как list of rows, row=0 — нижняя строка.
        """
        changed = False
        gained_total = 0
        for c in range(GRID_SIZE):
            col = [self.grid[r][c] for r in range(GRID_SIZE)]  # bottom -> top
            rev = list(reversed(col))  # top -> bottom
            new_rev, gained = self.merge_list_left(rev)  # сжать/слить к "верху"
            new_col = list(reversed(new_rev))  # вернуть порядок bottom -> top
            if new_col != col:
                changed = True
                for r in range(GRID_SIZE):
                    self.grid[r][c] = new_col[r]
                gained_total += gained
        if gained_total:
            self.score += gained_total
        return changed

    def move_down(self):
        """
        Переместить плитки вниз (в сторону уменьшения индекса row).
        """
        changed = False
        gained_total = 0
        for c in range(GRID_SIZE):
            col = [self.grid[r][c] for r in range(GRID_SIZE)]  # bottom -> top
            new_col, gained = self.merge_list_left(col)  # сжать/слить к низу (bottom)
            if new_col != col:
                changed = True
                for r in range(GRID_SIZE):
                    self.grid[r][c] = new_col[r]
                gained_total += gained
        if gained_total:
            self.score += gained_total
        return changed

    # ----------------------
    def has_moves_possible(self):
        """Проверить, есть ли ход (пустые ячейки или возможные слияния)."""
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == 0:
                    return True
                if c + 1 < GRID_SIZE and self.grid[r][c] == self.grid[r][c + 1]:
                    return True
                if r + 1 < GRID_SIZE and self.grid[r][c] == self.grid[r + 1][c]:
                    return True
        return False

    def check_game_end(self):
        """Проверить условия окончания игры: победа (2048) или отсутствие ходов (поражение)."""
        # Победа: есть плитка 2048
        for row in self.grid:
            for v in row:
                if v == 2048:
                    self.win = True
                    # Сохраняем результат, если он лучше, либо если файла best_score ещё нет
                    if self.score > self.best_score or not os.path.exists(BEST_SCORE_FILE):
                        self.best_score = self.score
                        self.save_best_score()
                    return
        # Поражение: нет возможных ходов
        if not self.has_moves_possible():
            self.game_over = True
            if self.score > self.best_score or not os.path.exists(BEST_SCORE_FILE):
                self.best_score = self.score
                self.save_best_score()

    def reset_game(self):
        """Сбросить игровое состояние для новой игры (сохранение Best не трогаем)."""
        self.grid = self.create_empty_grid(GRID_SIZE)
        self.score = 0
        self.game_over = False
        self.win = False
        self.spawn_initial_tiles(2)

    # ----------------------
    # Обработчик клавиш
    # ----------------------
    def on_key_press(self, key, modifiers):
        """Обрабатываем стрелки — перемещаем плитки к краю в направлении.
        R — рестарт игры."""
        # Рестарт игры по R
        if key == arcade.key.R:
            self.reset_game()
            return

        # Если игра закончена — игнорируем клавиши (кроме R)
        if self.game_over or self.win:
            return

        moved = False
        if key == arcade.key.LEFT:
            moved = self.move_left()
        elif key == arcade.key.RIGHT:
            moved = self.move_right()
        elif key == arcade.key.UP:
            moved = self.move_up()
        elif key == arcade.key.DOWN:
            moved = self.move_down()

        # Если поле изменилось — спавним новую плитку и обновляем best_score
        if moved:
            # Спавним одну плитку
            self.spawn_one_tile()

            # Обновляем best_score при необходимости и сохраняем
            if self.score > self.best_score:
                self.best_score = self.score
                self.save_best_score()

            # Проверяем окончание игры (победа/поражение)
            self.check_game_end()

            # Для отладки можно вывести сетку и счёт
            print("Moved — current grid:")
            for row in self.grid:
                print(row)
            print(f"Score: {self.score}  Best: {self.best_score}")

    # ----------------------
    # Рендер
    # ----------------------
    def on_draw(self):
        self.clear()
        self.draw_board()
        self.draw_score_boxes()

        # Оверлей при окончании игры
        if self.win or self.game_over:
            # затемняющий полупрозрачный слой
            arcade.draw_rect_filled(arcade.rect.XYWH(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0), (0, 0, 0, 150))
            center_x = WINDOW_WIDTH / 2
            center_y = WINDOW_HEIGHT / 2
            if self.win:
                msg = 'Вы выиграли. Нажмите "R" чтобы попробовать снова'
            else:
                msg = 'Вы проиграли. Нажмите "R" чтобы попробовать снова'
            arcade.draw_text(msg, center_x, center_y, TEXT_COLOR_LIGHT, 24, anchor_x="center", anchor_y="center")

    def draw_board(self):
        """Отрисовать все клетки и плитки с числами."""
        half = self.cell_size / 2
        tile_w = self.cell_size - CELL_PADDING
        tile_h = self.cell_size - CELL_PADDING

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                # Центр клетки
                x = self.field_offset_x + col * self.cell_size + half
                y = self.field_offset_y + row * self.cell_size + half

                value = self.grid[row][col]
                color = TILE_COLORS.get(value, TILE_COLORS[2048])
                arcade.draw_rect_filled(arcade.rect.XYWH(x, y, tile_w, tile_h), color)

                if value != 0:
                    font_size = max(12, int(self.cell_size * 0.45))
                    # Текст цвет зависит от величины
                    text_color = TEXT_COLOR_DARK if value <= 4 else TEXT_COLOR_LIGHT
                    arcade.draw_text(str(value), x, y, text_color, font_size, anchor_x="center", anchor_y="center")

    def draw_score_boxes(self):
        # Нарисовать два бокса Score и BestScore под полем (слева)
        box_w = self.field_pixel_size * 0.45
        box_h = 50
        left_x = self.field_offset_x + box_w / 2
        bottom_y = self.field_offset_y - box_h - 10

        # Score
        arcade.draw_rect_filled(arcade.rect.XYWH(left_x, bottom_y + box_h / 2, box_w, box_h), BOX_COLOR)
        arcade.draw_text(f"Score: {self.score}", left_x, bottom_y + box_h / 2, TEXT_COLOR_LIGHT, 20, anchor_x="center", anchor_y="center")

        # Best
        arcade.draw_rect_filled(arcade.rect.XYWH(left_x + box_w + 10, bottom_y + box_h / 2, box_w, box_h), BOX_COLOR)
        arcade.draw_text(f"Best: {self.best_score}", left_x + box_w + 10, bottom_y + box_h / 2, TEXT_COLOR_LIGHT, 20, anchor_x="center", anchor_y="center")

def main():
    Game2048()
    arcade.run()


if __name__ == "__main__":
    main()
