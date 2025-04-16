import tkinter as tk
from tkinter import messagebox, simpledialog
import time
import copy

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

        # Initialize grids
        self.pieces = [[0] * self.n for _ in range(self.n)]  # 0=empty, >0=White, <0=Black
        self.green_pieces = [[0] * self.n for _ in range(self.n)]  # Green count
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
        self.root.title("Stacking Game")
        self.main_canvas = tk.Canvas(root, width=self.n*self.cell_size, height=self.n*self.cell_size)
        self.main_canvas.pack()
        self.status_label = tk.Label(root, text=f"Current Player: {self.current_player}", font=("Arial", 12))
        self.status_label.pack()

        # Piece choice
        self.piece_var = tk.StringVar(value="White" if self.current_player == "White" else "Black")
        choice_frame = tk.Frame(root)
        choice_frame.pack()
        tk.Label(choice_frame, text="Piece:", font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Radiobutton(choice_frame, text="White", variable=self.piece_var, value="White",
                       command=self.update_piece_choice).pack(side=tk.LEFT)
        tk.Radiobutton(choice_frame, text="Black", variable=self.piece_var, value="Black",
                       command=self.update_piece_choice).pack(side=tk.LEFT)
        tk.Radiobutton(choice_frame, text="Green", variable=self.piece_var, value="Green",
                       command=self.update_piece_choice).pack(side=tk.LEFT)

        # Preview frame
        self.preview_frame = tk.Frame(root)
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

        # Buttons
        button_frame = tk.Frame(root)
        button_frame.pack()
        tk.Button(button_frame, text="Show White Boards", command=lambda: self.show_possible_boards("White")).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Show Black Boards", command=lambda: self.show_possible_boards("Black")).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Clear Boards", command=self.clear_preview).pack(side=tk.LEFT)

        # Draw main board
        self.tiles = {}
        for i in range(self.n):
            for j in range(self.n):
                x1, y1 = j * self.cell_size, i * self.cell_size
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                rect = self.main_canvas.create_rectangle(x1, y1, x2, y2, fill="lightgray", outline="black")
                text = self.main_canvas.create_text(x1 + self.cell_size/2, y1 + self.cell_size-10,
                                                  text=f"k={self.thresholds[i][j]}", font=("Arial", 10))
                self.tiles[(i, j)] = {"rect": rect, "text": text, "circles": [], "green_circles": []}
                self.main_canvas.tag_bind(rect, "<Button-1>", lambda event, row=i, col=j: self.handle_click(row, col))

        self.update_board()
        self.update_piece_choice()

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

    def update_piece_choice(self):
        for widget in self.root.winfo_children()[2].winfo_children()[1:3]:
            widget.config(state="normal")
        if self.current_player == "White":
            self.root.winfo_children()[2].winfo_children()[2].config(state="disabled")
        else:
            self.root.winfo_children()[2].winfo_children()[1].config(state="disabled")

    def get_possible_moves(self, piece_type):
        is_white = self.current_player == "White"
        moves = []
        for i in range(self.n):
            for j in range(self.n):
                count = abs(self.pieces[i][j])
                green = self.green_pieces[i][j]
                k = self.thresholds[i][j]
                total = count + green
                if piece_type == "Green":
                    if (not self.is_blocked(i, j) and total < k and
                        self.pieces[i][j] != 0):
                        moves.append((i, j))
                elif piece_type == self.current_player:
                    if (not self.is_blocked(i, j) and total < k and
                        (self.pieces[i][j] == 0 and green == 0 or
                         (self.pieces[i][j] > 0 and is_white) or
                         (self.pieces[i][j] < 0 and not is_white))):
                        moves.append((i, j))
        return moves

    def get_possible_boards(self, player):
        boards = []
        moves = self.get_possible_moves(player)
        for i, j in moves:
            new_pieces = copy.deepcopy(self.pieces)
            new_green = copy.deepcopy(self.green_pieces)
            new_pieces[i][j] = (abs(new_pieces[i][j]) + 1) if player == "White" else -(abs(new_pieces[i][j]) + 1)
            if abs(new_pieces[i][j]) == self.thresholds[i][j]:
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < self.n and 0 <= nj < self.n:
                        new_pieces[ni][nj] = 0
            boards.append({"pieces": new_pieces, "green_pieces": new_green, "move": (i, j), "piece_type": player})
        green_moves = self.get_possible_moves("Green")
        for i, j in green_moves:
            new_pieces = copy.deepcopy(self.pieces)
            new_green = copy.deepcopy(self.green_pieces)
            new_green[i][j] += 1
            boards.append({"pieces": new_pieces, "green_pieces": new_green, "move": (i, j), "piece_type": "Green"})
        return boards

    def show_possible_boards(self, player):
        self.clear_preview()
        self.possible_boards = self.get_possible_boards(player)
        for idx, board_info in enumerate(self.possible_boards):
            if idx >= len(self.preview_canvases):
                break
            canvas = self.preview_canvases[idx]
            label = self.preview_labels[idx]
            pieces = board_info["pieces"]
            green_pieces = board_info["green_pieces"]
            move = board_info["move"]
            piece_type = board_info["piece_type"]
            player_char = "W" if piece_type == "White" else "B" if piece_type == "Black" else "G"
            label.config(text=f"{player_char}: {move}")
            for i in range(self.n):
                for j in range(self.n):
                    x1, y1 = j * self.preview_cell_size, i * self.preview_cell_size
                    x2, y2 = x1 + self.preview_cell_size, y1 + self.preview_cell_size
                    count = abs(pieces[i][j])
                    green = green_pieces[i][j]
                    k = self.thresholds[i][j]
                    is_blocked = False
                    for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ni, nj = i + di, j + dj
                        if 0 <= ni < self.n and 0 <= nj < self.n:
                            if abs(pieces[ni][nj]) == self.thresholds[ni][nj]:
                                is_blocked = True
                                break
                    color = "lightgray"
                    if count == k:
                        color = "blue" if pieces[i][j] > 0 else "red"
                    elif is_blocked:
                        color = "yellow"
                    elif count > 0 or green > 0:
                        color = "#fff3b0" if pieces[i][j] > 0 else "#606c38"
                    canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                    canvas.create_text(x1 + self.preview_cell_size/2, y1 + self.preview_cell_size-8,
                                      text=f"k={k}", font=("Arial", 8))
                    # Assign pieces to 2x2 grid
                    grid_positions = [(12, 12), (28, 12), (12, 28), (28, 28)]
                    grid_idx = 0
                    # White/Black pieces
                    if count > 0:
                        is_white = pieces[i][j] > 0
                        for _ in range(count):
                            if grid_idx < k:
                                x, y = grid_positions[grid_idx]
                                canvas.create_oval(
                                    x1 + x - 4, y1 + y - 4,
                                    x1 + x + 4, y1 + y + 4,
                                    fill="white" if is_white else "black",
                                    outline="black"
                                )
                                grid_idx += 1
                    # Green pieces
                    for _ in range(green):
                        if grid_idx < k:
                            x, y = grid_positions[grid_idx]
                            canvas.create_oval(
                                x1 + x - 4, y1 + y - 4,
                                x1 + x + 4, y1 + y + 4,
                                fill="#2ecc71",
                                outline="black"
                            )
                            grid_idx += 1

    def clear_preview(self):
        self.possible_boards = []
        for canvas in self.preview_canvases:
            canvas.delete("all")
        for label in self.preview_labels:
            label.config(text="")

    def set_position(self, position, green_position):
        if len(position) != self.n or any(len(row) != self.n for row in position):
            raise ValueError("Position must be an n x n grid")
        if len(green_position) != self.n or any(len(row) != self.n for row in green_position):
            raise ValueError("Green position must be an n x n grid")
        for i in range(self.n):
            for j in range(self.n):
                count = position[i][j]
                green = green_position[i][j]
                k = self.thresholds[i][j]
                if abs(count) + green > k or green < 0:
                    raise ValueError(f"Invalid counts at ({i},{j}): |{count}| + {green} > k={k}")
                if green > 0 and count == 0:
                    raise ValueError(f"Green pieces require White/Black at ({i},{j})")
                self.pieces[i][j] = count
                self.green_pieces[i][j] = green
        self.update_board()
        self.clear_preview()

    def is_blocked(self, i, j):
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.n and 0 <= nj < self.n:
                if abs(self.pieces[ni][nj]) == self.thresholds[ni][nj]:
                    return True
        return False

    def apply_attacker_effects(self, i, j):
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if 0 <= ni < self.n and 0 <= nj < self.n:
                if self.pieces[ni][nj] != 0:
                    self.pieces[ni][nj] = 0
                    self.green_pieces[ni][nj] = 0
                    self.animate_removal(ni, nj)

    def animate_removal(self, i, j):
        if self.animating:
            return
        self.animating = True
        rect = self.tiles[(i, j)]["rect"]
        circles = self.tiles[(i, j)]["circles"] + self.tiles[(i, j)]["green_circles"]
        original_color = "lightgray"
        for circle in circles:
            self.main_canvas.delete(circle)
        self.tiles[(i, j)]["circles"] = []
        self.tiles[(i, j)]["green_circles"] = []
        self.main_canvas.itemconfig(rect, fill="yellow")
        self.root.update()
        self.root.after(200, lambda: self.main_canvas.itemconfig(rect, fill=original_color))
        self.root.after(400, lambda: self.main_canvas.itemconfig(rect, fill="yellow"))
        self.root.after(600, lambda: self.main_canvas.itemconfig(rect, fill=original_color))
        self.root.after(800, lambda: setattr(self, "animating", False))
        self.update_board()

    def animate_placement(self, i, j, piece_type):
        if self.animating:
            return
        self.animating = True
        x1, y1 = j * self.cell_size, i * self.cell_size
        count = abs(self.pieces[i][j])
        green_count = self.green_pieces[i][j]
        k = self.thresholds[i][j]
        is_white = self.pieces[i][j] > 0 if count > 0 else self.current_player == "White"
        for circle in self.tiles[(i, j)]["circles"] + self.tiles[(i, j)]["green_circles"]:
            self.main_canvas.delete(circle)
        self.tiles[(i, j)]["circles"] = []
        self.tiles[(i, j)]["green_circles"] = []
        # 2x2 grid positions
        grid_positions = [(25, 25), (55, 25), (25, 55), (55, 55)]
        grid_idx = 0
        # White/Black circles
        for _ in range(count):
            if grid_idx < k:
                x, y = grid_positions[grid_idx]
                circle = self.main_canvas.create_oval(
                    x1 + x - 7, y1 + y - 7,
                    x1 + x + 7, y1 + y + 7,
                    fill="white" if is_white else "black",
                    outline="black",
                    state="hidden"
                )
                self.tiles[(i, j)]["circles"].append(circle)
                grid_idx += 1
        # Green circles
        for _ in range(green_count):
            if grid_idx < k:
                x, y = grid_positions[grid_idx]
                circle = self.main_canvas.create_oval(
                    x1 + x - 7, y1 + y - 7,
                    x1 + x + 7, y1 + y + 7,
                    fill="#2ecc71",
                    outline="black",
                    state="hidden"
                )
                self.tiles[(i, j)]["green_circles"].append(circle)
                grid_idx += 1
        # Animate
        for step in range(10):
            for circle in self.tiles[(i, j)]["circles"] + self.tiles[(i, j)]["green_circles"]:
                self.main_canvas.itemconfig(circle, state="normal")
                scale = 0.5 + step * 0.05
                x, y, x2, y2 = self.main_canvas.coords(circle)
                cx, cy = (x + x2) / 2, (y + y2) / 2
                self.main_canvas.coords(circle,
                                       cx - 7 * scale, cy - 7 * scale,
                                       cx + 7 * scale, cy + 7 * scale)
            self.root.update()
            time.sleep(0.05)
        self.animating = False
        self.update_board()

    def handle_click(self, i, j):
        if self.animating:
            return
        piece_type = self.piece_var.get()
        is_white = self.current_player == "White"
        count = abs(self.pieces[i][j])
        green = self.green_pieces[i][j]
        k = self.thresholds[i][j]
        total = count + green

        if piece_type != "Green" and piece_type != self.current_player:
            messagebox.showinfo("Invalid Choice", f"{self.current_player} cannot place {piece_type}!")
            return
        if piece_type == "Green":
            if self.is_blocked(i, j) or total >= k or self.pieces[i][j] == 0:
                messagebox.showinfo("Invalid Move", "Cannot place Green piece here!")
                return
        else:
            if (self.is_blocked(i, j) or total >= k or
                (self.pieces[i][j] < 0 and is_white) or
                (self.pieces[i][j] > 0 and not is_white) or
                (self.pieces[i][j] == 0 and green > 0)):
                messagebox.showinfo("Invalid Move", "Cannot place piece here!")
                return

        self.clear_preview()
        if piece_type == "Green":
            self.green_pieces[i][j] += 1
        else:
            self.pieces[i][j] = (abs(self.pieces[i][j]) + 1) if is_white else -(abs(self.pieces[i][j]) + 1)
        self.animate_placement(i, j, piece_type)

        if abs(self.pieces[i][j]) == k:
            self.apply_attacker_effects(i, j)
            self.main_canvas.itemconfig(self.tiles[(i, j)]["rect"],
                                      fill="blue" if is_white else "red")

        self.update_board()
        self.current_player = "Black" if self.current_player == "White" else "White"
        self.status_label.config(text=f"Current Player: {self.current_player}")
        self.update_piece_choice()

        if not self.has_legal_moves():
            winner = "Black" if self.current_player == "White" else "White"
            messagebox.showinfo("Game Over", f"{winner} wins!")
            self.root.quit()

    def has_legal_moves(self):
        for piece_type in [self.current_player, "Green"]:
            if self.get_possible_moves(piece_type):
                return True
        return False

    def update_board(self):
        for i in range(self.n):
            for j in range(self.n):
                count = abs(self.pieces[i][j])
                green_count = self.green_pieces[i][j]
                k = self.thresholds[i][j]
                rect = self.tiles[(i, j)]["rect"]
                text = self.tiles[(i, j)]["text"]
                self.main_canvas.itemconfig(text, text=f"k={k}")
                if count == k:
                    self.main_canvas.itemconfig(rect, fill="blue" if self.pieces[i][j] > 0 else "red")
                elif self.is_blocked(i, j):
                    self.main_canvas.itemconfig(rect, fill="yellow")
                elif count > 0 or green_count > 0:
                    self.main_canvas.itemconfig(rect, fill="#fff3b0" if self.pieces[i][j] > 0 else "#606c38")
                else:
                    self.main_canvas.itemconfig(rect, fill="lightgray")
                x1, y1 = j * self.cell_size, i * self.cell_size
                for circle in self.tiles[(i, j)]["circles"] + self.tiles[(i, j)]["green_circles"]:
                    self.main_canvas.delete(circle)
                self.tiles[(i, j)]["circles"] = []
                self.tiles[(i, j)]["green_circles"] = []
                # 2x2 grid positions
                grid_positions = [(25, 25), (55, 25), (25, 55), (55, 55)]
                grid_idx = 0
                # White/Black pieces
                if count > 0:
                    is_white = self.pieces[i][j] > 0
                    for _ in range(count):
                        if grid_idx < k:
                            x, y = grid_positions[grid_idx]
                            circle = self.main_canvas.create_oval(
                                x1 + x - 7, y1 + y - 7,
                                x1 + x + 7, y1 + y + 7,
                                fill="white" if is_white else "black",
                                outline="black"
                            )
                            self.tiles[(i, j)]["circles"].append(circle)
                            grid_idx += 1
                # Green pieces
                for _ in range(green_count):
                    if grid_idx < k:
                        x, y = grid_positions[grid_idx]
                        circle = self.main_canvas.create_oval(
                            x1 + x - 7, y1 + y - 7,
                            x1 + x + 7, y1 + y + 7,
                            fill="#2ecc71",
                            outline="black"
                        )
                        self.tiles[(i, j)]["green_circles"].append(circle)
                        grid_idx += 1

def main():
    root = tk.Tk()
    game = StackingGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()