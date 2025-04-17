import tkinter as tk
from tkinter import messagebox, simpledialog
import time
import copy
import random

class StackingGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Stacking Game Setup")
        
        # Prompt for board size
        self.n = self.get_board_size()
        if self.n is None:
            root.destroy()
            return
            
        self.cell_size = 100
        self.preview_cell_size = 50
        self.current_player = "White"
        self.animating = False
        self.possible_boards = []
        self.white_ai = tk.BooleanVar(value=False)
        self.black_ai = tk.BooleanVar(value=False)
        self.white_ai_locked = False
        self.black_ai_locked = False
        self.auto_play_active = False

        # Scrollable canvas setup
        self.canvas = tk.Canvas(root, width=550, height=700)
        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas)
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # Update scroll region
        self.content_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Mouse wheel scrolling
        def on_mouse_wheel(event):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
        self.canvas.bind_all("<Button-4>", on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", on_mouse_wheel)

        # Initialize grids
        self.pieces = [[0] * self.n for _ in range(self.n)]  # 0=empty, >0=White, <0=Black
        self.thresholds = [[0] * self.n for _ in range(self.n)]
        for i in range(self.n):
            for j in range(self.n):
                k = 0
                if i > 0: k += 1
                if i < self.n-1: k += 1
                if j > 0: k += 1
                if j < self.n-1: k += 1
                self.thresholds[i][j] = k

        # Main GUI setup
        self.main_canvas = tk.Canvas(self.content_frame, width=self.n*self.cell_size, height=self.n*self.cell_size)
        self.main_canvas.pack()
        self.status_label = tk.Label(self.content_frame, text=f"Current Player: {self.current_player}", font=("Arial", 12))
        self.status_label.pack()

        # Preview frame
        self.preview_frame = tk.Frame(self.content_frame)
        self.preview_frame.pack()
        self.preview_canvases = []
        self.preview_labels = []
        for row in range(2):
            for col in range(5):
                if row * 5 + col < 9:
                    canvas = tk.Canvas(self.preview_frame, width=self.n*self.preview_cell_size,
                                      height=self.n*self.preview_cell_size, bg="white")
                    canvas.grid(row=row, column=col, padx=5, pady=5)
                    label = tk.Label(self.preview_frame, text="", font=("Arial", 8))
                    label.grid(row=row+1, column=col)
                    self.preview_canvases.append(canvas)
                    self.preview_labels.append(label)

        # Buttons and AI controls (below preview frame)
        button_frame = tk.Frame(self.content_frame)
        button_frame.pack()
        tk.Button(button_frame, text="Show White Boards", command=lambda: self.show_possible_boards("White")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Show Black Boards", command=lambda: self.show_possible_boards("Black")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear Boards", command=self.clear_preview).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Auto Play", command=self.auto_play).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Restart", command=self.restart_game).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Stop Auto Play", command=self.stop_auto_play).pack(side=tk.LEFT, padx=5)

        # AI toggles
        ai_frame = tk.Frame(self.content_frame)
        ai_frame.pack()
        self.white_ai_checkbutton = tk.Checkbutton(ai_frame, text="White AI", variable=self.white_ai, command=self.check_ai_move)
        self.white_ai_checkbutton.pack(side=tk.LEFT, padx=5)
        self.black_ai_checkbutton = tk.Checkbutton(ai_frame, text="Black AI", variable=self.black_ai, command=self.check_ai_move)
        self.black_ai_checkbutton.pack(side=tk.LEFT, padx=5)

        # Draw main board
        self.tiles = {}
        for i in range(self.n):
            for j in range(self.n):
                x1, y1 = j * self.cell_size, i * self.cell_size
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                rect = self.main_canvas.create_rectangle(x1, y1, x2, y2, fill="lightgray", outline="black")
                text = self.main_canvas.create_text(x1 + self.cell_size/2, y1 + self.cell_size-10,
                                                  text=f"k={self.thresholds[i][j]}", font=("Arial", 10))
                self.tiles[(i, j)] = {"rect": rect, "text": text, "circles": []}
                self.main_canvas.tag_bind(rect, "<Button-1>", lambda event, row=i, col=j: self.handle_click(row, col))

        self.update_board()
        self.check_ai_move()

    def get_board_size(self):
        """Prompt user for board size and validate input."""
        while True:
            try:
                n = simpledialog.askinteger("Input", "Enter board size (n for n x n board, 2-10):",
                                          parent=self.root, minvalue=2, maxvalue=10)
                if n is None:  # User cancelled
                    return None
                return n
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a number between 2 and 10.")
                continue

    def get_possible_moves(self, player):
        is_white = player == "White"
        moves = []
        for i in range(self.n):
            for j in range(self.n):
                current_pieces = self.pieces[i][j]
                k = self.thresholds[i][j]
                if (not self.is_blocked(i, j) and
                    (current_pieces == 0 or
                     (current_pieces > 0 and is_white and current_pieces < k) or
                     (current_pieces < 0 and not is_white and -current_pieces < k))):
                    moves.append((i, j))
        print(f"Possible moves for {player}: {moves}, Board: {self.pieces}")
        return moves

    def get_best_move(self, player):
        moves = self.get_possible_moves(player)
        if not moves:
            print(f"No valid moves for {player}")
            return None
        # Prioritize empty tiles with max k
        empty_moves = [(i, j) for i, j in moves if self.pieces[i][j] == 0]
        if empty_moves:
            max_k = max(self.thresholds[i][j] for i, j in empty_moves)
            best_moves = [(i, j) for i, j in empty_moves if self.thresholds[i][j] == max_k]
            print(f"Empty moves for {player}: {best_moves}, max_k={max_k}")
            return random.choice(best_moves)
        # No empty tiles: pick own-color tile with min k
        is_white = player == "White"
        own_moves = [(i, j) for i, j in moves if (self.pieces[i][j] > 0 and is_white) or (self.pieces[i][j] < 0 and not is_white)]
        if own_moves:
            min_k = min(self.thresholds[i][j] for i, j in own_moves)
            best_moves = [(i, j) for i, j in own_moves if self.thresholds[i][j] == min_k]
            print(f"Own moves for {player}: {best_moves}, min_k={min_k}")
            return random.choice(best_moves)
        # Fallback: any valid move
        print(f"Fallback moves for {player}: {moves}")
        return random.choice(moves)

    def get_possible_boards(self, player):
        is_white = player == "White"
        moves = []
        for i, j in self.get_possible_moves(player):
            new_board = copy.deepcopy(self.pieces)
            new_board[i][j] = (abs(new_board[i][j]) + 1) if is_white else -(abs(new_board[i][j]) + 1)
            if abs(new_board[i][j]) == self.thresholds[i][j]:
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < self.n and 0 <= nj < self.n:
                        new_board[ni][nj] = 0
            moves.append({"board": new_board, "move": (i, j)})
        return moves

    def show_possible_boards(self, player):
        self.clear_preview()
        self.possible_boards = self.get_possible_boards(player)
        for idx, board_info in enumerate(self.possible_boards):
            if idx >= len(self.preview_canvases):
                break
            canvas = self.preview_canvases[idx]
            label = self.preview_labels[idx]
            board = board_info["board"]
            move = board_info["move"]
            player_char = "W" if player == "White" else "B"
            label.config(text=f"{player_char}: {move}")
            for i in range(self.n):
                for j in range(self.n):
                    x1, y1 = j * self.preview_cell_size, i * self.preview_cell_size
                    x2, y2 = x1 + self.preview_cell_size, y1 + self.preview_cell_size
                    is_blocked = False
                    for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ni, nj = i + di, j + dj
                        if 0 <= ni < self.n and 0 <= nj < self.n:
                            if abs(board[ni][nj]) == self.thresholds[ni][nj]:
                                is_blocked = True
                                break
                    count = abs(board[i][j])
                    color = "lightgray"
                    if count == self.thresholds[i][j]:
                        color = "blue" if board[i][j] > 0 else "red"
                    elif is_blocked:
                        color = "yellow"
                    canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                    canvas.create_text(x1 + self.preview_cell_size/2, y1 + self.preview_cell_size-8,
                                      text=f"k={self.thresholds[i][j]}", font=("Arial", 8))
                    if count > 0:
                        is_white = board[i][j] > 0
                        for p in range(count):
                            offset_x = 10 + (p % 2) * 15
                            offset_y = 10 + (p // 2) * 15
                            canvas.create_oval(
                                x1 + offset_x, y1 + offset_y,
                                x1 + offset_x + 10, y1 + offset_y + 10,
                                fill="white" if is_white else "black",
                                outline="black"
                            )

    def clear_preview(self):
        self.possible_boards = []
        for canvas in self.preview_canvases:
            canvas.delete("all")
        for label in self.preview_labels:
            label.config(text="")

    def set_position(self, position):
        if len(position) != self.n or any(len(row) != self.n for row in position):
            raise ValueError("Position must be an n x n grid")
        for i in range(self.n):
            for j in range(self.n):
                count = position[i][j]
                k = self.thresholds[i][j]
                if abs(count) > k:
                    raise ValueError(f"Invalid piece count at ({i},{j}): |{count}| > k={k}")
                self.pieces[i][j] = count
        self.update_board()
        self.clear_preview()

    def is_blocked(self, i, j):
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.n and 0 <= nj < self.n:
                if abs(self.pieces[ni][nj]) == self.thresholds[ni][nj]:
                    print(f"Blocked at ({i},{j}) by attacker at ({ni},{nj})")
                    return True
        return False

    def apply_attacker_effects(self, i, j):
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.n and 0 <= nj < self.n:
                if self.pieces[ni][nj] != 0:
                    print(f"Clearing ({ni},{nj}) due to attacker at ({i},{j})")
                    self.pieces[ni][nj] = 0
                    self.animate_removal(ni, nj)

    def animate_removal(self, i, j):
        if self.animating:
            return
        self.animating = True
        rect = self.tiles[(i, j)]["rect"]
        circles = self.tiles[(i, j)]["circles"]
        original_color = "lightgray"
        for circle in circles:
            self.main_canvas.delete(circle)
        self.tiles[(i, j)]["circles"] = []
        self.main_canvas.itemconfig(rect, fill="yellow")
        self.root.update()
        self.root.after(200, lambda: self.main_canvas.itemconfig(rect, fill=original_color))
        self.root.after(400, lambda: self.main_canvas.itemconfig(rect, fill="yellow"))
        self.root.after(600, lambda: self.main_canvas.itemconfig(rect, fill=original_color))
        self.root.after(800, lambda: setattr(self, "animating", False))
        self.update_board()

    def animate_placement(self, i, j, player, is_ai=False):
        if self.animating:
            return
        self.animating = True
        x1, y1 = j * self.cell_size, i * self.cell_size
        count = abs(self.pieces[i][j])
        k = self.thresholds[i][j]
        is_white = player == "White"
        for circle in self.tiles[(i, j)]["circles"]:
            self.main_canvas.delete(circle)
        self.tiles[(i, j)]["circles"] = []
        for p in range(count):
            offset_x = 20 + (p % 2) * 30
            offset_y = 20 + (p // 2) * 30
            circle = self.main_canvas.create_oval(
                x1 + offset_x, y1 + offset_y,
                x1 + offset_x + 20, y1 + offset_y + 20,
                fill="white" if is_white else "black",
                outline="black",
                state="hidden"
            )
            self.tiles[(i, j)]["circles"].append(circle)
        if is_ai:
            self.main_canvas.itemconfig(self.tiles[(i, j)]["rect"], outline="green", width=3)
        for step in range(10):
            for circle in self.tiles[(i, j)]["circles"]:
                self.main_canvas.itemconfig(circle, state="normal")
                scale = 0.5 + step * 0.05
                self.main_canvas.coords(circle,
                                       x1 + offset_x - 10 * scale, y1 + offset_y - 10 * scale,
                                       x1 + offset_x + 10 * scale, y1 + offset_y + 10 * scale)
            self.root.update()
            time.sleep(0.05)
        for p, circle in enumerate(self.tiles[(i, j)]["circles"]):
            offset_x = 20 + (p % 2) * 30
            offset_y = 20 + (p // 2) * 30
            self.main_canvas.coords(circle,
                                   x1 + offset_x, y1 + offset_y,
                                   x1 + offset_x + 20, y1 + offset_y + 20)
        if is_ai:
            self.root.after(200, lambda: self.main_canvas.itemconfig(self.tiles[(i, j)]["rect"], outline="black", width=1))
        self.animating = False
        self.update_board()

    def handle_click(self, i, j):
        if self.auto_play_active:
            return
        if self.animating:
            return
        if ((self.current_player == "White" and self.white_ai.get()) or
            (self.current_player == "Black" and self.black_ai.get())):
            return
        if not self.has_legal_moves():
            self.end_game()
            return
        current_pieces = self.pieces[i][j]
        k = self.thresholds[i][j]
        is_white = self.current_player == "White"
        if (self.is_blocked(i, j) or
            (current_pieces < 0 and is_white) or
            (current_pieces > 0 and not is_white) or
            abs(current_pieces) >= k):
            messagebox.showinfo("Invalid Move", "Cannot place piece here!")
            return

        self.clear_preview()
        self.pieces[i][j] = (abs(current_pieces) + 1) if is_white else -(abs(current_pieces) + 1)
        self.animate_placement(i, j, self.current_player, is_ai=False)
        self.status_label.config(text=f"Player Move: ({i},{j})")

        if abs(self.pieces[i][j]) == k:
            self.apply_attacker_effects(i, j)
            self.main_canvas.itemconfig(self.tiles[(i, j)]["rect"],
                                      fill="blue" if is_white else "red")

        self.update_board()
        self.current_player = "Black" if self.current_player == "White" else "White"
        self.status_label.config(text=f"Current Player: {self.current_player}")

        if not self.has_legal_moves():
            self.end_game()
        else:
            self.check_ai_move()

    def make_ai_move(self):
        move = self.get_best_move(self.current_player)
        if not move:
            return False
        i, j = move
        is_white = self.current_player == "White"
        self.clear_preview()
        self.pieces[i][j] = (abs(self.pieces[i][j]) + 1) if is_white else -(abs(self.pieces[i][j]) + 1)
        self.animate_placement(i, j, self.current_player, is_ai=True)
        self.status_label.config(text=f"AI Move: ({i},{j}), k={self.thresholds[i][j]}")

        if abs(self.pieces[i][j]) == self.thresholds[i][j]:
            self.apply_attacker_effects(i, j)
            self.main_canvas.itemconfig(self.tiles[(i, j)]["rect"],
                                      fill="blue" if is_white else "red")

        self.update_board()
        self.current_player = "Black" if self.current_player == "White" else "White"
        self.status_label.config(text=f"Current Player: {self.current_player}")
        return True

    def check_ai_move(self):
        if self.white_ai.get() and not self.white_ai_locked:
            self.white_ai_checkbutton.config(state="disabled")
            self.white_ai_locked = True
        if self.black_ai.get() and not self.black_ai_locked:
            self.black_ai_checkbutton.config(state="disabled")
            self.black_ai_locked = True
        if ((self.current_player == "White" and self.white_ai.get()) or
            (self.current_player == "Black" and self.black_ai.get())):
            self.run_ai_turn()

    def run_ai_turn(self):
        if self.auto_play_active:
            return
        if self.animating:
            print("Waiting for animation, retrying")
            self.root.after(100, self.run_ai_turn)
            return
        if not self.has_legal_moves():
            self.end_game()
            return
        print(f"AI turn: {self.current_player}, Board: {self.pieces}")
        if self.make_ai_move():
            if not self.has_legal_moves():
                self.end_game()
                return
            if ((self.current_player == "White" and self.white_ai.get()) or
                (self.current_player == "Black" and self.black_ai.get())):
                self.root.after(500, self.run_ai_turn)

    def auto_play(self):
        if self.auto_play_active:
            return
        self.auto_play_active = True
        self.white_ai.set(True)
        self.black_ai.set(True)
        self.white_ai_checkbutton.config(state="disabled")
        self.black_ai_checkbutton.config(state="disabled")
        self.white_ai_locked = True
        self.black_ai_locked = True
        self.run_auto_play()

    def stop_auto_play(self):
        self.auto_play_active = False
        self.status_label.config(text=f"Auto Play Stopped, Current Player: {self.current_player}")
        self.check_ai_move()

    def run_auto_play(self):
        if not self.auto_play_active:
            print("Auto play stopped")
            return
        if self.animating:
            self.root.after(100, self.run_auto_play)
            return
        if not self.has_legal_moves():
            self.end_game()
            return
        print(f"Auto play: {self.current_player}'s turn, Board: {self.pieces}")
        self.make_ai_move()
        if not self.has_legal_moves():
            self.end_game()
            return
        self.root.after(500, self.run_auto_play)

    def end_game(self):
        winner = "Black" if self.current_player == "White" else "White"
        messagebox.showinfo("Game Over", f"{winner} wins!")
        self.white_ai_checkbutton.config(state="normal")
        self.black_ai_checkbutton.config(state="normal")
        self.white_ai_locked = False
        self.black_ai_locked = False
        self.auto_play_active = False
        self.status_label.config(text=f"Game Over, Winner: {winner}")
        print(f"Game over, winner: {winner}, Board: {self.pieces}")

    def restart_game(self):
        self.pieces = [[0] * self.n for _ in range(self.n)]
        self.current_player = "White"
        self.animating = False
        self.possible_boards = []
        self.white_ai.set(False)
        self.black_ai.set(False)
        self.white_ai_checkbutton.config(state="normal")
        self.black_ai_checkbutton.config(state="normal")
        self.white_ai_locked = False
        self.black_ai_locked = False
        self.auto_play_active = False
        self.status_label.config(text=f"Current Player: {self.current_player}")
        self.clear_preview()
        self.update_board()
        self.check_ai_move()

    def has_legal_moves(self):
        is_white = self.current_player == "White"
        for i in range(self.n):
            for j in range(self.n):
                current_pieces = self.pieces[i][j]
                k = self.thresholds[i][j]
                if (not self.is_blocked(i, j) and
                    (current_pieces == 0 or
                     (current_pieces > 0 and is_white and current_pieces < k) or
                     (current_pieces < 0 and not is_white and -current_pieces < k))):
                    return True
        print(f"No legal moves for {self.current_player}, Board: {self.pieces}")
        return False

    def update_board(self):
        for i in range(self.n):
            for j in range(self.n):
                count = abs(self.pieces[i][j])
                k = self.thresholds[i][j]
                rect = self.tiles[(i, j)]["rect"]
                text = self.tiles[(i, j)]["text"]
                self.main_canvas.itemconfig(text, text=f"k={k}")
                if count == k:
                    self.main_canvas.itemconfig(rect, fill="blue" if self.pieces[i][j] > 0 else "red")
                elif self.is_blocked(i, j):
                    self.main_canvas.itemconfig(rect, fill="yellow")
                else:
                    self.main_canvas.itemconfig(rect, fill="lightgray")
                x1, y1 = j * self.cell_size, i * self.cell_size
                for circle in self.tiles[(i, j)]["circles"]:
                    self.main_canvas.delete(circle)
                self.tiles[(i, j)]["circles"] = []
                if count > 0:
                    is_white = self.pieces[i][j] > 0
                    for p in range(count):
                        offset_x = 20 + (p % 2) * 30
                        offset_y = 20 + (p // 2) * 30
                        circle = self.main_canvas.create_oval(
                            x1 + offset_x, y1 + offset_y,
                            x1 + offset_x + 20, y1 + offset_y + 20,
                            fill="white" if is_white else "black",
                            outline="black"
                        )
                        self.tiles[(i, j)]["circles"].append(circle)

def main():
    root = tk.Tk()
    game = StackingGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()