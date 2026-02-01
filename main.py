import os
import json
import random
from pyglet.graphics import Batch
import arcade
from arcade.gui import UIManager, UIFlatButton
from arcade.gui.widgets.layout import UIAnchorLayout, UIBoxLayout
from arcade import load_texture, SpriteSolidColor
from arcade.gui.widgets.buttons import UIFlatButton



WINDOW_WIDTH = 720
WINDOW_HEIGHT = 720
FIELD_SCALE = 0.8
CELL_PADDING = 6

BACKGROUND_COLOR = (187, 173, 160)
MENU_COLOR = (205, 173, 160)
TILE_COLORS = {
    0: (205, 193, 180), 2: (238, 228, 218), 4: (237, 224, 200),
    8: (242, 177, 121), 16: (245, 149, 99), 32: (246, 124, 95),
    64: (246, 94, 59), 128: (237, 207, 114), 256: (237, 204, 97),
    512: (237, 200, 80), 1024: (237, 197, 63), 2048: (237, 194, 46)
}
BOX_COLOR = (119, 110, 101)
TEXT_COLOR_LIGHT = arcade.color.WHITE
TEXT_COLOR_DARK = arcade.color.BLACK

BEST_SCORE_FILE = os.path.join(os.path.expanduser("~"), ".2048_best_score.json")


class Game2048(arcade.View):
    def __init__(self, grid_size=4):
        super().__init__()
        self.grid_size = grid_size
        self.field_pixel_size = int(min(WINDOW_WIDTH, WINDOW_HEIGHT) * FIELD_SCALE)
        self.cell_size = self.field_pixel_size / grid_size
        self.field_offset_x = (WINDOW_WIDTH - self.field_pixel_size) / 2
        self.field_offset_y = (WINDOW_HEIGHT - self.field_pixel_size) / 2

        self.grid = self.create_empty_grid(grid_size)
        self.score = 0
        self.best_score = self.load_best_score()
        self.game_over = False
        self.win = False
        self.spawn_initial_tiles(2)

    def load_best_score(self):
        try:
            with open(BEST_SCORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("best_score", 0))
        except Exception:
            pass

    def save_best_score(self):
        try:
            with open(BEST_SCORE_FILE, "w", encoding="utf-8") as f:
                json.dump({"best_score": int(self.best_score)}, f)
        except Exception:
            pass

    def create_empty_grid(self, n):
        return [[0] * n for _ in range(n)]

    def spawn_initial_tiles(self, count=2):
        n = self.grid_size ** 2
        count = min(count, n)
        indices = random.sample(range(n), count)
        for idx in indices:
            row, col = divmod(idx, self.grid_size)
            self.grid[row][col] = 2

    def spawn_one_tile(self):
        empty = [(r, c) for r in range(self.grid_size) for c in range(self.grid_size) if self.grid[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.grid[r][c] = 4 if random.random() < 0.1 else 2

    @staticmethod
    def compress_list_left(line):
        nonzeros = [x for x in line if x]
        return nonzeros + [0] * (len(line) - len(nonzeros))

    @staticmethod
    def merge_list_left(line):
        nonzeros = [x for x in line if x]
        merged, score = [], 0
        i = 0
        while i < len(nonzeros):
            if i + 1 < len(nonzeros) and nonzeros[i] == nonzeros[i + 1]:
                val = nonzeros[i] * 2
                merged.append(val)
                score += val
                i += 2
            else:
                merged.append(nonzeros[i])
                i += 1
        return merged + [0] * (len(line) - len(merged)), score

    def move_left(self):
        changed = False
        score_gained = 0
        for r in range(self.grid_size):
            old = self.grid[r][:]
            new, gained = self.merge_list_left(old)
            if new != old:
                changed = True
                self.grid[r] = new
                score_gained += gained
        self.score += score_gained
        return changed

    def move_right(self):
        changed = False
        score_gained = 0
        for r in range(self.grid_size):
            old = self.grid[r][:]
            rev_old = old[::-1]
            new_rev, gained = self.merge_list_left(rev_old)
            new = new_rev[::-1]
            if new != old:
                changed = True
                self.grid[r] = new
                score_gained += gained
        self.score += score_gained
        return changed

    def move_up(self):
        changed = False
        score_gained = 0
        for c in range(self.grid_size):
            col = [self.grid[r][c] for r in range(self.grid_size)]
            rev_col = col[::-1]
            new_rev, gained = self.merge_list_left(rev_col)
            new_col = new_rev[::-1]
            if new_col != col:
                changed = True
                for r in range(self.grid_size):
                    self.grid[r][c] = new_col[r]
                score_gained += gained
        self.score += score_gained
        return changed

    def move_down(self):
        changed = False
        score_gained = 0
        for c in range(self.grid_size):
            col = [self.grid[r][c] for r in range(self.grid_size)]
            new_col, gained = self.merge_list_left(col)
            if new_col != col:
                changed = True
                for r in range(self.grid_size):
                    self.grid[r][c] = new_col[r]
                score_gained += gained
        self.score += score_gained
        return changed

    def has_moves_possible(self):
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] == 0:
                    return True
                if c + 1 < self.grid_size and self.grid[r][c] == self.grid[r][c + 1]:
                    return True
                if r + 1 < self.grid_size and self.grid[r][c] == self.grid[r + 1][c]:
                    return True
        return False

    def check_game_end(self):
        for row in self.grid:
            if 2048 in row:
                self.win = True
                if self.score > self.best_score or not os.path.exists(BEST_SCORE_FILE):
                    self.best_score = self.score
                    self.save_best_score()
                return
        if not self.has_moves_possible():
            self.game_over = True
            if self.score > self.best_score or not os.path.exists(BEST_SCORE_FILE):
                self.best_score = self.score
                self.save_best_score()

    def reset_game(self):
        self.grid = self.create_empty_grid(self.grid_size)
        self.score = 0
        self.game_over = self.win = False
        self.spawn_initial_tiles(2)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.R:
            self.reset_game()
            return
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

        if key == arcade.key.ESCAPE:
            menu_view = MenuView()
            self.window.show_view(menu_view)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, BACKGROUND_COLOR)
        self.draw_board()
        self.draw_score_boxes()

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
        tile_size = self.cell_size - CELL_PADDING
        half_tile = tile_size / 2

        for r in range(self.grid_size):
            for c in range(self.grid_size):
                # Центр клетки
                x = self.field_offset_x + c * self.cell_size + self.cell_size / 2
                y = self.field_offset_y + r * self.cell_size + self.cell_size / 2
                value = self.grid[r][c]
                color = TILE_COLORS.get(value, TILE_COLORS[2048])

                arcade.draw_lbwh_rectangle_filled(x - half_tile, y - half_tile, tile_size, tile_size, color)

                if value:
                    font_size = max(24, int(self.cell_size * 0.45))
                    text_color = TEXT_COLOR_DARK if value <= 4 else TEXT_COLOR_LIGHT
                    arcade.draw_text(str(value), x, y, text_color, font_size,
                                     anchor_x="center", anchor_y="center")

    def draw_score_boxes(self):
        # Нарисовать два бокса Score и BestScore под полем (слева)
        box_w = self.field_pixel_size * 0.45
        box_h = 50
        left_x = self.field_offset_x + box_w / 2
        bottom_y = self.field_offset_y - box_h - 10

        # Score
        arcade.draw_rect_filled(arcade.rect.XYWH(left_x, bottom_y + box_h / 2, box_w, box_h), BOX_COLOR)
        arcade.draw_text(f"Score: {self.score}", left_x, bottom_y + box_h / 2, TEXT_COLOR_LIGHT, 20, anchor_x="center",
                         anchor_y="center")

        # Best
        arcade.draw_rect_filled(arcade.rect.XYWH(left_x + box_w + 10, bottom_y + box_h / 2, box_w, box_h), BOX_COLOR)
        arcade.draw_text(f"Best: {self.best_score}", left_x + box_w + 10, bottom_y + box_h / 2, TEXT_COLOR_LIGHT, 20,
                         anchor_x="center", anchor_y="center")


class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = (205, 193, 180)
        self.manager = UIManager()
        self.comic_font = "Comic Sans MS"
        self.anchor_layout = UIAnchorLayout()
        self.manager.add(self.anchor_layout)

        self.setup_widgets()
        self.setup_title()

    def setup_title(self):
        title_color = (14, 33, 75)
        self.main_text = arcade.Text(
            "2048", self.window.width / 2, self.window.height - 120,
            title_color, 60, font_name=self.comic_font, anchor_x="center", bold=True
        )
        self.space_text = arcade.Text(
            "Выбери поле, чтобы начать!", self.window.width / 2, self.window.height - 180,
            title_color, 30, font_name=self.comic_font, anchor_x="center"
        )

    def draw_text_outline(self, text, x, y, color, font_size, outline_color=arcade.color.WHITE, outline_width=3):
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    arcade.draw_text(text, x + dx, y + dy + 30, outline_color, font_size, font_name=self.comic_font, anchor_x="center", anchor_y="center")
        arcade.draw_text(text, x, y + 30, color, font_size, font_name=self.comic_font, anchor_x="center", anchor_y="center")

    def setup_widgets(self):
        self.flat_button_4 = UIFlatButton(text="4x4", width=320, height=75, text_color=arcade.color.WHITE, bg_color=arcade.color.BLUE)
        self.anchor_layout.add(
            self.flat_button_4,
            anchor_x="center_x",  # Якорь по X: левый край, центр или правый
            align_x=0,  # Смещение по X в пикселях от якоря
            anchor_y="top",  # Якорь по Y: bottom, center_y или top
            align_y=-250  # Смещение по Y в пикселях от якоря (отрицательное — вниз)
        )
        self.flat_button_4.on_click = lambda e, s=4: self.window.show_view(Game2048(s))

        self.flat_button_5 = UIFlatButton(text="5x5", width=320, height=75, color=arcade.color.BLUE)
        self.flat_button_5.on_click = lambda e, s=5: self.window.show_view(Game2048(s))
        self.anchor_layout.add(
            self.flat_button_5,
            anchor_x="center_x",  # Якорь по X: левый край, центр или правый
            align_x=0,  # Смещение по X в пикселях от якоря
            anchor_y="top",  # Якорь по Y: bottom, center_y или top
            align_y=-350  # Смещение по Y в пикселях от якоря (отрицательное — вниз)
        )

        self.flat_button_7 = UIFlatButton(text="7x7", width=320, height=75, color=arcade.color.BLUE)
        self.flat_button_7.on_click = lambda e, s=7: self.window.show_view(Game2048(s))
        self.anchor_layout.add(
            self.flat_button_7,
            anchor_x="center_x",  # Якорь по X: левый край, центр или правый
            align_x=0,  # Смещение по X в пикселях от якоря
            anchor_y="top",  # Якорь по Y: bottom, center_y или top
            align_y=-450  # Смещение по Y в пикселях от якоря (отрицательное — вниз)
        )

        self.flat_button_lider = UIFlatButton(text='Лидеры', width=150, height=60, font='Comic Sans MS',
                                              color=arcade.color.BLUE)
        self.anchor_layout.add(
            self.flat_button_lider,
            anchor_x="center_x",  # Якорь по X: левый край, центр или правый
            align_x=-175,  # Смещение по X в пикселях от якоря
            anchor_y="top",  # Якорь по Y: bottom, center_y или top
            align_y=-600  # Смещение по Y в пикселях от якоря (отрицательное — вниз)
        )


        self.flat_button_rules = UIFlatButton(text="Правила", width=150, height=60, color=arcade.color.BLUE)
        self.anchor_layout.add(
            self.flat_button_rules,
            anchor_x="center_x",  # Якорь по X: левый край, центр или правый
            align_x=0,  # Смещение по X в пикселях от якоря
            anchor_y="top",  # Якорь по Y: bottom, center_y или top
            align_y=-600  # Смещение по Y в пикселях от якоря (отрицательное — вниз)
        )
        self.flat_button_rules.on_click = lambda event: self.window.show_view(Rules())

        self.flat_button_odds = UIFlatButton(text="Шансы", width=150, height=60, color=arcade.color.BLUE)
        self.anchor_layout.add(
            self.flat_button_odds,
            anchor_x="center_x",  # Якорь по X: левый край, центр или правый
            align_x=175,  # Смещение по X в пикселях от якоря
            anchor_y="top",  # Якорь по Y: bottom, center_y или top
            align_y=-600  # Смещение по Y в пикселях от якоря (отрицательное — вниз)
        )
        self.flat_button_odds.on_click = lambda event: self.window.show_view(Chance())

    def on_show_view(self):
        self.manager.enable()

    def on_hide_view(self):
        self.manager.disable()

    def on_draw(self):
        self.clear()
        self.manager.draw()

        self.draw_text_outline(
            "2048", self.window.width / 2, self.window.height - 120,
            (14, 33, 75), 72, outline_color=arcade.color.WHITE, outline_width=4
        )
        self.draw_text_outline(
            "Выбери поле, чтобы начать!", self.window.width / 2, self.window.height - 200,
            (14, 33, 75), 22, outline_color=arcade.color.WHITE, outline_width=2
        )


class Rules(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = UIManager()
        self.comic_font = "Comic Sans MS"
        self.anchor_layout = UIAnchorLayout()
        self.manager.add(self.anchor_layout)
        self.setup_widgets()

    def setup_widgets(self):
        back_btn = UIFlatButton(
            text="Назад",
            width=200,
            height=60,
            font_size=24,
            font_name="Comic Sans MS",
            color=(205, 193, 180),
            text_color=(14, 33, 75)
        )
        back_btn.on_click = lambda event: self.window.show_view(MenuView())


        self.anchor_layout.add(back_btn, anchor_x="center_x", anchor_y="center_y", align_x=200, align_y= -300)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, (205, 193, 180))

        self.manager.draw()

        arcade.draw_text("Правила игры 2048:", WINDOW_WIDTH / 2, WINDOW_HEIGHT - 75,
                         (14, 33, 75), 32, anchor_x="center", font_name=self.comic_font)

        y_pos = WINDOW_HEIGHT - 350
        arcade.draw_text(
            "• Игровое поле имеет форму квадрата 4×4 / 5x5 / 7x7.В начале игры появляются две плитки номинала «2» или «4».\n"
            "•Нажатием стрелки игрок может скинуть все плитки игрового поля в одну из четырёх сторон.\n"
            "•Если при сбрасывании две плитки одного номинала «налетают» одна на другую, то они превращаются в одну, номинал которой равен сумме соединившихся плиток.\n"
            "•После каждого хода на свободной секции поля появляется новая плитка номиналом «2» или «4».\n"
            "•Если при нажатии кнопки местоположение плиток или их номинал не изменится, то ход не совершается.\n"
            "•Если в одной строчке или в одном столбце находится более двух плиток одного номинала, то при сбрасывании они начинают соединяться с той стороны, в которую были направлены.\n"
            "•За каждое соединение игровые очки увеличиваются на номинал получившейся плитки.\n"
            "•Игра заканчивается поражением, если после очередного хода невозможно совершить действие.",
            WINDOW_WIDTH / 2, y_pos,
            (14, 33, 75), 14,
            anchor_x="center", anchor_y="center",
            font_name=self.comic_font,
            multiline=True,
            width=600
        )


        arcade.draw_text("Нажмите ESC или кнопку 'Назад'", 230, 50,
                         (14, 33, 75), 20, anchor_x="center", font_name=self.comic_font)



    def on_show_view(self):
        self.manager.enable()
        arcade.set_background_color(205, 193, 180)

    def on_hide_view(self):
        self.manager.disable()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(MenuView())


class Chance(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = UIManager()
        self.comic_font = "Comic Sans MS"
        self.anchor_layout = UIAnchorLayout()
        self.manager.add(self.anchor_layout)
        self.setup_widgets()

    def setup_widgets(self):
        back_btn = UIFlatButton(
            text="Назад",
            width=200,
            height=60,
            font_size=24,
            font_name="Comic Sans MS",
            color=(205, 193, 180),
            text_color=(14, 33, 75)
        )
        back_btn.on_click = lambda event: self.window.show_view(MenuView())


        self.anchor_layout.add(back_btn, anchor_x="center_x", anchor_y="center_y", align_x=200, align_y= -300)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, (205, 193, 180))

        self.manager.draw()

        # Заголовок
        arcade.draw_text("Шансы появления плиток:", WINDOW_WIDTH / 2, WINDOW_HEIGHT - 100,
                         (14, 33, 75), 32, anchor_x="center", font_name=self.comic_font)

        # Информация о шансах
        y_pos = WINDOW_HEIGHT / 2 + 50
        arcade.draw_text("• 75% — новая плитка со значением 2", WINDOW_WIDTH / 2, y_pos,
                         (14, 33, 75), 28, anchor_x="center", font_name=self.comic_font)
        arcade.draw_text("• 25% — новая плитка со значением 4", WINDOW_WIDTH / 2, y_pos - 80,
                         (14, 33, 75), 28, anchor_x="center", font_name=self.comic_font)

        arcade.draw_text("Нажмите ESC или кнопку 'Назад'", 230, 50,
                         (14, 33, 75), 20, anchor_x="center", font_name=self.comic_font)



    def on_show_view(self):
        self.manager.enable()
        arcade.set_background_color(205, 193, 180)

    def on_hide_view(self):
        self.manager.disable()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(MenuView())


window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, "2048 - Меню")
menu_view = MenuView()
window.show_view(menu_view)
arcade.run()
