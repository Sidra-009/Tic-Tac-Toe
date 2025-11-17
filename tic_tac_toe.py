# Feature-complete revamp implementing requested UI, fixes and improvements.
# - Responsive board scaling and perfect click detection
# - Start menu with modes
# - Light theme with enhanced UI
# - Glass UI elements
# - Minimax AI
# - Smooth mark animations, winning-line animation
# - Soft music and sound effects (generated)
#
# Run: python light_tictactoe.py
# Requires pygame

import pygame
import sys
import math
import random
import time
from array import array
from typing import List, Optional, Tuple

# ====== Configuration / Defaults ======
DEFAULT_WIDTH, DEFAULT_HEIGHT = 900, 700
FPS = 60

# Marks
PLAYER_X = 'X'
PLAYER_O = 'O'

# Win combos
WIN_COMBINATIONS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6)
]


# ====== Audio helpers ======
def setup_audio():
    # lower latency recommended settings
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass


def make_tone(freq=440.0, duration=0.25, volume=0.18, sample_rate=44100):
    """
    Generate a simple sine tone as pygame.Sound.
    If creation fails, returns None.
    """
    try:
        n = int(sample_rate * duration)
        arr = array('h')
        amp = int(32767 * volume)
        for i in range(n):
            t = float(i) / sample_rate
            v = int(amp * math.sin(2.0 * math.pi * freq * t))
            arr.append(v)
            arr.append(v)  # stereo
        sound = pygame.mixer.Sound(buffer=arr.tobytes())
        return sound
    except Exception:
        return None


# ====== Theme Manager ======
class ThemeManager:
    def __init__(self):
        # Light theme palette
        self.primary = pygame.Color('#4a6fa5')  # Soft blue
        self.secondary = pygame.Color('#ff7e5f')  # Coral
        self.accent = pygame.Color('#6b5b95')  # Purple
        self.white = pygame.Color('#ffffff')
        self.light_gray = pygame.Color('#f8f9fa')
        self.medium_gray = pygame.Color('#e9ecef')
        self.dark_gray = pygame.Color('#495057')
        self.black = pygame.Color('#212529')

        self.themes = {
            'light': {
                'bg_a': pygame.Color('#f8f9fa'),
                'bg_b': pygame.Color('#e9ecef'),
                'panel': pygame.Color('#ffffff'),
                'cell_top': pygame.Color('#ffffff'),
                'cell_bottom': pygame.Color('#f1f3f4'),
                'line': pygame.Color('#adb5bd'),
                'glass': pygame.Color(255, 255, 255),
                'glow': self.primary,
                'text': self.dark_gray,
                'text_light': self.medium_gray
            }
        }
        self.mode = 'light'

    def theme(self):
        return self.themes[self.mode]


# ====== Simple UI Button ======
class Button:
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                 color_a: pygame.Color, color_b: pygame.Color, radius=14, callback=None):
        self.rect = rect
        self.text = text
        self.font = font
        self.color_a = color_a
        self.color_b = color_b
        self.radius = radius
        self.callback = callback
        self.hover = False
        self.active = True

    def draw(self, surf):
        if not self.active:
            # dimmed
            base = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            pygame.draw.rect(base, (200, 200, 200, 200), base.get_rect(), border_radius=self.radius)
            surf.blit(base, self.rect.topleft)
            txt = self.font.render(self.text, True, (160, 160, 160))
            surf.blit(txt, (self.rect.x + (self.rect.w - txt.get_width()) // 2,
                            self.rect.y + (self.rect.h - txt.get_height()) // 2))
            return

        tmp = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        # gradient fill
        for y in range(self.rect.h):
            t = y / max(1, self.rect.h - 1)
            c = self.color_a.lerp(self.color_b, t)
            pygame.draw.line(tmp, c, (0, y), (self.rect.w, y))
        # border radius
        mask = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255), mask.get_rect(), border_radius=self.radius)
        tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        
        # subtle shadow
        shadow = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 30), shadow.get_rect(), border_radius=self.radius)
        surf.blit(shadow, (self.rect.x + 2, self.rect.y + 3))
        
        # highlight on hover
        if self.hover:
            highlight = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            pygame.draw.rect(highlight, (255, 255, 255, 40), highlight.get_rect(), border_radius=self.radius)
            tmp.blit(highlight, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
        surf.blit(tmp, self.rect.topleft)
        
        # text with subtle shadow
        txt_shadow = self.font.render(self.text, True, (0, 0, 0, 30))
        surf.blit(txt_shadow, (self.rect.x + (self.rect.w - txt_shadow.get_width()) // 2 + 1,
                              self.rect.y + (self.rect.h - txt_shadow.get_height()) // 2 + 1))
        
        txt = self.font.render(self.text, True, (255, 255, 255))
        surf.blit(txt, (self.rect.x + (self.rect.w - txt.get_width()) // 2,
                        self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle_event(self, event):
        if not self.active:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False


# ====== Board ======
class Board:
    def __init__(self):
        # 9 cells: None, 'X', 'O'
        self.cells: List[Optional[str]] = [None] * 9
        # animations: dict idx -> {'start': timestamp, 'type': 'appear'}
        self.anim = {}
        self.winning_combo: Optional[Tuple[int, int, int]] = None
        self.win_anim_start = None

    def reset(self):
        self.cells = [None] * 9
        self.anim.clear()
        self.winning_combo = None
        self.win_anim_start = None

    def place(self, idx: int, mark: str):
        if 0 <= idx < 9 and self.cells[idx] is None:
            self.cells[idx] = mark
            self.anim[idx] = {'start': pygame.time.get_ticks()}
            return True
        return False

    def winner(self) -> Tuple[Optional[str], Optional[Tuple[int, int, int]]]:
        for a, b, c in WIN_COMBINATIONS:
            if self.cells[a] and self.cells[a] == self.cells[b] == self.cells[c]:
                return self.cells[a], (a, b, c)
        if all(c is not None for c in self.cells):
            return 'Draw', None
        return None, None

    def is_cell_hover(self, idx, board_rect, cell_size, mouse_pos):
        row = idx // 3
        col = idx % 3
        x = board_rect.x + col * cell_size
        y = board_rect.y + row * cell_size
        inner = pygame.Rect(x + 12, y + 12, int(cell_size) - 24, int(cell_size) - 24)
        return inner.collidepoint(mouse_pos)

    def draw(self, surf, board_rect: pygame.Rect, cell_size: int, fonts: dict,
             theme: dict, mouse_pos, colors):
        # board with subtle shadow
        board_shadow = pygame.Surface((board_rect.w + 10, board_rect.h + 10), pygame.SRCALPHA)
        pygame.draw.rect(board_shadow, (0, 0, 0, 40), board_shadow.get_rect(), border_radius=20)
        surf.blit(board_shadow, (board_rect.x - 5, board_rect.y - 5))
        
        # MAIN BOARD SURFACE - WHITE BACKGROUND
        board_surf = pygame.Surface((board_rect.w, board_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(board_surf, (*theme['panel'][:3], 255), board_surf.get_rect(), border_radius=16)

        # BOLD GRID LINES - CLEARLY VISIBLE
        line_width = 6
        line_color = (*theme['line'][:3], 255)  # Solid gray lines
        
        # Draw horizontal lines
        for r in range(1, 3):
            y = int(r * cell_size)
            pygame.draw.line(board_surf, line_color, (10, y), (board_rect.w - 10, y), line_width)
        
        # Draw vertical lines  
        for c in range(1, 3):
            x = int(c * cell_size)
            pygame.draw.line(board_surf, line_color, (x, 10), (x, board_rect.h - 10), line_width)

        # draw cells
        for i in range(9):
            row = i // 3
            col = i % 3
            x = int(col * cell_size)
            y = int(row * cell_size)
            
            # Cell area (slightly smaller than the grid cell)
            cell_inner = pygame.Rect(x + 8, y + 8, int(cell_size) - 16, int(cell_size) - 16)
            
            # Create cell surface
            cell_surf = pygame.Surface((cell_inner.w, cell_inner.h), pygame.SRCALPHA)
            
            # White cell background
            pygame.draw.rect(cell_surf, (*theme['cell_top'][:3], 255), cell_surf.get_rect(), border_radius=10)

            idx_global = i
            mark = self.cells[idx_global]
            if mark:
                anim = self.anim.get(idx_global)
                t = 1.0
                if anim:
                    elapsed = (pygame.time.get_ticks() - anim['start']) / 420.0
                    t = min(max(elapsed, 0.0), 1.0)
                alpha = int(255 * t)
                scale = 0.6 + 0.4 * t
                
                # mark color mapping: X -> blue, O -> coral
                if mark == PLAYER_X:
                    color = colors['x']
                    glow_col = colors['x_glow']
                else:
                    color = colors['o']
                    glow_col = colors['o_glow']
                    
                # render text once at big size and scale
                mark_surf = fonts['mark'].render(mark, True, color)
                mw, mh = mark_surf.get_size()
                target_w = int(mw * scale)
                target_h = int(mh * scale)
                mark_surf = pygame.transform.smoothscale(mark_surf, (target_w, target_h))
                mark_surf.set_alpha(alpha)
                
                # Center the mark in the cell
                mark_x = (cell_inner.w - mark_surf.get_width()) // 2
                mark_y = (cell_inner.h - mark_surf.get_height()) // 2
                
                # Draw the mark
                cell_surf.blit(mark_surf, (mark_x, mark_y))

            # hovered highlight if empty
            hover = cell_inner.collidepoint(mouse_pos) and (mark is None)
            if hover:
                highlight = pygame.Surface((cell_inner.w, cell_inner.h), pygame.SRCALPHA)
                pygame.draw.rect(highlight, (*theme['glow'][:3], 30), highlight.get_rect(), border_radius=10)
                cell_surf.blit(highlight, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            # Draw the cell onto the board
            board_surf.blit(cell_surf, (x + 8, y + 8))

        # blit board_surf onto main surface
        surf.blit(board_surf, board_rect.topleft)

        # winning animation overlay
        if self.winning_combo:
            if self.win_anim_start is None:
                self.win_anim_start = pygame.time.get_ticks()
            elapsed = (pygame.time.get_ticks() - self.win_anim_start) / 1000.0
            # animate a bright line across winning cell centers
            a, b, c = self.winning_combo
            ax = board_rect.x + (a % 3) * cell_size + cell_size // 2
            ay = board_rect.y + (a // 3) * cell_size + cell_size // 2
            cx = board_rect.x + (c % 3) * cell_size + cell_size // 2
            cy = board_rect.y + (c // 3) * cell_size + cell_size // 2
            # pulsing width and alpha
            width = int(8 + 6 * math.sin(elapsed * 8))
            alpha = int(180 + 40 * math.sin(elapsed * 3))
            line_surf = pygame.Surface((surf.get_width(), surf.get_height()), pygame.SRCALPHA)
            pygame.draw.line(line_surf, (*theme['glow'][:3], max(0, alpha)), (ax, ay), (cx, cy), width)
            surf.blit(line_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            # highlight winning cells
            for idx in self.winning_combo:
                row = idx // 3
                col = idx % 3
                x = int(board_rect.x + col * cell_size + 8)
                y = int(board_rect.y + row * cell_size + 8)
                w = int(cell_size) - 16
                h = int(cell_size) - 16
                highlight = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.rect(highlight, (*theme['glow'][:3], 40), highlight.get_rect(), border_radius=10)
                surf.blit(highlight, (x, y), special_flags=pygame.BLEND_RGBA_ADD)


# ====== AI ======
class AI:
    def __init__(self, ai_mark=PLAYER_O, human_mark=PLAYER_X, difficulty='Impossible'):
        self.ai_mark = ai_mark
        self.human_mark = human_mark
        self.difficulty = difficulty  # 'Easy', 'Medium', 'Impossible'

    def best_move(self, cells: List[Optional[str]]) -> Optional[int]:
        # choose strategy based on difficulty
        available = [i for i, c in enumerate(cells) if c is None]
        if not available:
            return None
        if self.difficulty == 'Easy':
            return random.choice(available)
        if self.difficulty == 'Medium':
            # attempt best with depth-limited minimax, but occasionally randomize
            if random.random() < 0.35:
                return random.choice(available)
            _, move = self._minimax(cells[:], True, -9999, 9999, 0, max_depth=4)
            return move if move is not None else random.choice(available)
        # Impossible: full minimax
        _, move = self._minimax(cells[:], True, -9999, 9999, 0, max_depth=9)
        return move

    def _minimax(self, board: List[Optional[str]], is_max: bool, alpha: int, beta: int, depth: int, max_depth: int) -> Tuple[int, Optional[int]]:
        w = self._check_winner(board)
        if w == self.ai_mark:
            return 100 - depth, None
        if w == self.human_mark:
            return -100 + depth, None
        if w == 'Draw':
            return 0, None
        if depth >= max_depth:
            return 0, None

        if is_max:
            best_val = -9999
            best_move = None
            for i in range(9):
                if board[i] is None:
                    board[i] = self.ai_mark
                    val, _ = self._minimax(board, False, alpha, beta, depth + 1, max_depth)
                    board[i] = None
                    if val > best_val:
                        best_val = val
                        best_move = i
                    alpha = max(alpha, best_val)
                    if beta <= alpha:
                        break
            return best_val, best_move
        else:
            best_val = 9999
            best_move = None
            for i in range(9):
                if board[i] is None:
                    board[i] = self.human_mark
                    val, _ = self._minimax(board, True, alpha, beta, depth + 1, max_depth)
                    board[i] = None
                    if val < best_val:
                        best_val = val
                        best_move = i
                    beta = min(beta, best_val)
                    if beta <= alpha:
                        break
            return best_val, best_move

    def _check_winner(self, board: List[Optional[str]]) -> Optional[str]:
        for a, b, c in WIN_COMBINATIONS:
            if board[a] and board[a] == board[b] == board[c]:
                return board[a]
        if all(cell is not None for cell in board):
            return 'Draw'
        return None


# ====== Main Game ======
class Game:
    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        setup_audio()
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Tic Tac Toe - Light Edition")
        self.clock = pygame.time.Clock()
        self.running = True

        # Fonts
        self.font_title = pygame.font.SysFont('Segoe UI', 46, bold=True)
        self.font_sub = pygame.font.SysFont('Segoe UI', 20)
        self.font_small = pygame.font.SysFont('Segoe UI', 16)
        self.font_mark = pygame.font.SysFont('Segoe UI', 140, bold=True)
        self.font_button = pygame.font.SysFont('Segoe UI', 22, bold=True)

        # theme manager
        self.theme_mgr = ThemeManager()

        # board & AI
        self.board = Board()
        self.current_player = PLAYER_X
        self.ai = AI(ai_mark=PLAYER_O, human_mark=PLAYER_X, difficulty='Impossible')

        # sounds
        self.snd_click = make_tone(880, 0.04, 0.12)
        self.snd_place = make_tone(680, 0.06, 0.13)
        self.snd_win = make_tone(440, 0.35, 0.18)
        self.snd_draw = make_tone(250, 0.30, 0.15)
        self.music = make_tone(110, 4.0, 0.04)

        try:
            if self.music:
                self.music.play(loops=-1)
        except Exception:
            pass

        # game state
        self.mode = 'menu'  # 'menu', 'playing', 'gameover'
        self.vs_ai = True
        self.scores = {'Player': 0, 'AI': 0, 'Draws': 0}
        self.winner = None
        self.winning_combo = None
        self.last_move_time = 0

        # UI elements: created in setup_ui
        self.ui_buttons = []
        self.setup_menu_ui()

        # restart/change mode buttons (bottom)
        self.btn_restart = Button(pygame.Rect(0, 0, 160, 46), 'Restart', self.font_button,
                                  pygame.Color('#4a6fa5'), pygame.Color('#6b5b95'), radius=14, callback=self.reset_game)
        self.btn_change_mode = Button(pygame.Rect(0, 0, 160, 46), 'Menu', self.font_button,
                                      pygame.Color('#ff7e5f'), pygame.Color('#6b5b95'), radius=14, callback=self.open_menu)

        self.last_resize = (self.width, self.height)

        # AI scheduling
        self.ai_delay_until = 0

    def setup_menu_ui(self):
        # Buttons for menu - simplified with only two main options
        self.ui_buttons = []
        
        # Player vs Player
        def set_pvp():
            self.vs_ai = False
            self.mode = 'playing'
            self.reset_game()
            
        # Player vs AI
        def set_pvai():
            self.vs_ai = True
            self.mode = 'playing'
            self.reset_game()

        # Create buttons with proper positioning
        btn_w, btn_h = 280, 56
        spacing = 20
        
        b1 = Button(pygame.Rect(0, 0, btn_w, btn_h), 'Player vs Player', self.font_button,
                    pygame.Color('#4a6fa5'), pygame.Color('#6b5b95'), callback=set_pvp)
        b2 = Button(pygame.Rect(0, 0, btn_w, btn_h), 'Player vs AI', self.font_button,
                    pygame.Color('#ff7e5f'), pygame.Color('#6b5b95'), callback=set_pvai)

        self.ui_buttons = [b1, b2]

    def open_menu(self):
        self.mode = 'menu'
        self.setup_menu_ui()

    def reset_game(self):
        self.board.reset()
        self.current_player = PLAYER_X
        self.game_over_reset()

    def game_over_reset(self):
        self.winner = None
        self.winning_combo = None
        self.board.winning_combo = None
        self.board.win_anim_start = None
        self.mode = 'playing'

    def compute_layout(self):
        w, h = self.screen.get_size()
        
        # Board layout - properly centered
        max_board_size = min(w * 0.7, h * 0.6, 600)
        board_size = (max_board_size // 3) * 3  # Ensure divisible by 3
        cell_size = board_size // 3
        board_left = (w - board_size) // 2
        board_top = (h - board_size) // 2 - 20  # Slightly above center for title space
        board_rect = pygame.Rect(board_left, board_top, board_size, board_size)
        
        # Bottom buttons - centered
        total_btn_width = self.btn_restart.rect.w + self.btn_change_mode.rect.w + 20
        start_x = (w - total_btn_width) // 2
        self.btn_restart.rect.topleft = (start_x, h - 70)
        self.btn_change_mode.rect.topleft = (start_x + self.btn_restart.rect.w + 20, h - 70)
        
        # Menu buttons - properly centered
        if self.ui_buttons:
            total_menu_height = len(self.ui_buttons) * self.ui_buttons[0].rect.h + (len(self.ui_buttons) - 1) * 20
            start_y = (h - total_menu_height) // 2
            
            for i, button in enumerate(self.ui_buttons):
                button.rect.centerx = w // 2
                button.rect.y = start_y + i * (button.rect.h + 20)
        
        return board_rect, cell_size

    def check_end(self):
        w, combo = self.board.winner()
        if w is not None:
            self.mode = 'gameover'
            self.winner = w
            self.winning_combo = combo
            self.board.winning_combo = combo
            if w == PLAYER_X:
                self.scores['Player'] += 1
            elif w == PLAYER_O:
                self.scores['AI'] += 1
            else:
                self.scores['Draws'] += 1
            # sounds
            if w == 'Draw':
                if self.snd_draw:
                    try:
                        self.snd_draw.play()
                    except Exception:
                        pass
            else:
                if self.snd_win:
                    try:
                        self.snd_win.play()
                    except Exception:
                        pass

    def handle_click_board(self, mouse_pos, board_rect, cell_size):
        if self.mode != 'playing':
            return
        # compute col/row
        if not board_rect.collidepoint(mouse_pos):
            return
        local_x = mouse_pos[0] - board_rect.x
        local_y = mouse_pos[1] - board_rect.y
        col = int(local_x // cell_size)
        row = int(local_y // cell_size)
        idx = row * 3 + col
        if 0 <= idx < 9:
            if self.board.cells[idx] is None:
                # place for current player (human)
                placed = self.board.place(idx, self.current_player)
                if placed:
                    if self.snd_place:
                        try:
                            self.snd_place.play()
                        except Exception:
                            pass
                    self.last_move_time = pygame.time.get_ticks()
                    self.check_end()
                    # toggle turn
                    if self.mode != 'gameover':
                        if self.vs_ai:
                            # schedule AI
                            self.current_player = PLAYER_O
                            self.ai_delay_until = pygame.time.get_ticks() + 340
                        else:
                            self.current_player = PLAYER_O if self.current_player == PLAYER_X else PLAYER_X

    def ai_turn(self):
        # AI only acts in 'playing', vs_ai True, and when it's O's turn
        if not self.vs_ai or self.mode != 'playing':
            return
        if self.current_player != PLAYER_O:
            return
        if pygame.time.get_ticks() < getattr(self, 'ai_delay_until', 0):
            return
        move = self.ai.best_move(self.board.cells[:])
        if move is not None:
            self.board.place(move, PLAYER_O)
            if self.snd_place:
                try:
                    self.snd_place.play()
                except Exception:
                    pass
        self.last_move_time = pygame.time.get_ticks()
        self.check_end()
        if self.mode != 'gameover':
            self.current_player = PLAYER_X

    def draw_background(self):
        th = self.theme_mgr.theme()
        w, h = self.screen.get_size()
        # gradient background
        for y in range(h):
            t = y / max(1, h - 1)
            c = th['bg_a'].lerp(th['bg_b'], t)
            pygame.draw.line(self.screen, c, (0, y), (w, y))
            
        # Add subtle pattern
        pattern = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(0, w, 40):
            for j in range(0, h, 40):
                pygame.draw.circle(pattern, (255, 255, 255, 5), (i, j), 1)
        self.screen.blit(pattern, (0, 0))

    def draw_title(self):
        w, h = self.screen.get_size()
        title_text = "Tic Tac Toe"
        # subtle color
        col = self.theme_mgr.primary
        title_surf = self.font_title.render(title_text, True, col)
        
        # Add subtle shadow
        shadow_surf = self.font_title.render(title_text, True, (0, 0, 0, 30))
        x = (w - title_surf.get_width()) // 2
        self.screen.blit(shadow_surf, (x + 2, 32))
        self.screen.blit(title_surf, (x, 30))

    def draw_scoreboard(self):
        w, h = self.screen.get_size()
        th = self.theme_mgr.theme()
        sb_w, sb_h = 360, 50
        sb_x = (w - sb_w) // 2
        sb_y = h - 130
        
        # Shadow
        sb_shadow = pygame.Surface((sb_w + 6, sb_h + 6), pygame.SRCALPHA)
        pygame.draw.rect(sb_shadow, (0, 0, 0, 30), sb_shadow.get_rect(), border_radius=14)
        self.screen.blit(sb_shadow, (sb_x - 3, sb_y - 3))
        
        # Main panel
        sb = pygame.Surface((sb_w, sb_h), pygame.SRCALPHA)
        pygame.draw.rect(sb, (*th['panel'][:3], 240), sb.get_rect(), border_radius=12)
        
        ptxt = self.font_sub.render(f'Player: {self.scores["Player"]}', True, self.theme_mgr.primary)
        aitxt = self.font_sub.render(f'AI: {self.scores["AI"]}', True, self.theme_mgr.secondary)
        dtxt = self.font_sub.render(f'Draws: {self.scores["Draws"]}', True, self.theme_mgr.accent)
        sb.blit(ptxt, (20, 14))
        sb.blit(aitxt, (140, 14))
        sb.blit(dtxt, (220, 14))
        self.screen.blit(sb, (sb_x, sb_y))

    def draw_footer_buttons(self):
        self.btn_restart.draw(self.screen)
        self.btn_change_mode.draw(self.screen)

    def run(self):
        while self.screen is None:
            pygame.time.wait(10)
            
        while self.running:
            dt = self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    if event.key == pygame.K_r:
                        self.reset_game()
                # UI input
                if self.mode == 'menu':
                    for b in self.ui_buttons:
                        b.handle_event(event)
                elif self.mode == 'playing':
                    self.btn_restart.handle_event(event)
                    self.btn_change_mode.handle_event(event)
                elif self.mode == 'gameover':
                    self.btn_restart.handle_event(event)
                    self.btn_change_mode.handle_event(event)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.mode == 'menu':
                        # menu button clicks
                        for b in self.ui_buttons:
                            clicked = b.handle_event(event)
                    elif self.mode in ('playing', 'gameover'):
                        board_rect, cell_size = self.compute_layout()
                        # only process board click if game active and not over
                        if self.mode == 'playing':
                            self.handle_click_board(mouse_pos, board_rect, cell_size)

            # Updates
            if self.mode == 'playing':
                # AI tick
                self.ai_turn()

            # Draw pipeline
            self.draw_background()
            self.draw_title()

            # compute layout
            board_rect, cell_size = self.compute_layout()

            # UI elements
            if self.mode == 'menu':
                # Menu screen
                for b in self.ui_buttons:
                    b.draw(self.screen)
                    
                # Add subtitle
                subtitle = self.font_sub.render("Select Game Mode", True, self.theme_mgr.dark_gray)
                w, h = self.screen.get_size()
                self.screen.blit(subtitle, ((w - subtitle.get_width()) // 2, 
                                           self.ui_buttons[0].rect.y - 60))
            else:
                # Game screen
                # scoreboard
                self.draw_scoreboard()
                # board
                colors = {
                    'x': self.theme_mgr.primary,
                    'o': self.theme_mgr.secondary,
                    'x_glow': self.theme_mgr.primary,
                    'o_glow': self.theme_mgr.secondary
                }
                self.board.draw(self.screen, board_rect, cell_size, {'mark': self.font_mark}, self.theme_mgr.theme(),
                                mouse_pos, colors)
                # footer buttons
                self.draw_footer_buttons()
                # show current turn
                turn_text = f"Turn: {'You' if self.current_player == PLAYER_X else 'AI' if self.vs_ai else 'Player 2'}"
                t_surf = self.font_sub.render(turn_text, True, self.theme_mgr.dark_gray)
                self.screen.blit(t_surf, (20, 100))

            # if gameover draw modal
            if self.mode == 'gameover':
                # blur snapshot
                snap = self.screen.copy()
                small = pygame.transform.smoothscale(snap, (max(1, self.screen.get_width() // 12), max(1, self.screen.get_height() // 12)))
                blur = pygame.transform.smoothscale(small, self.screen.get_size())
                blur.set_alpha(180)
                self.screen.blit(blur, (0, 0))
                
                # modal box with shadow
                mw, mh = 500, 200
                mx = (self.screen.get_width() - mw) // 2
                my = (self.screen.get_height() - mh) // 2
                
                modal_shadow = pygame.Surface((mw + 10, mh + 10), pygame.SRCALPHA)
                pygame.draw.rect(modal_shadow, (0, 0, 0, 80), modal_shadow.get_rect(), border_radius=18)
                self.screen.blit(modal_shadow, (mx - 5, my - 5))
                
                modal = pygame.Surface((mw, mh), pygame.SRCALPHA)
                pygame.draw.rect(modal, (255, 255, 255, 240), modal.get_rect(), border_radius=16)
                # title
                if self.winner == PLAYER_X:
                    title = "You Win!" if not self.vs_ai else "Player Wins!"
                    color = self.theme_mgr.primary
                elif self.winner == PLAYER_O:
                    title = "AI Wins!" if self.vs_ai else "Player 2 Wins!"
                    color = self.theme_mgr.secondary
                else:
                    title = "It's a Draw!"
                    color = self.theme_mgr.accent
                    
                ts = self.font_title.render(title, True, color)
                modal.blit(ts, ((mw - ts.get_width()) // 2, 40))
                self.screen.blit(modal, (mx, my))
                
                # draw restart/change mode buttons on modal area
                self.btn_restart.draw(self.screen)
                self.btn_change_mode.draw(self.screen)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


def main():
    g = Game()
    g.run()


if __name__ == '__main__':
    main()