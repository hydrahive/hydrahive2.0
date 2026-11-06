extends Node2D

func _ready() -> void:
    queue_redraw()

func _process(_delta: float) -> void:
    queue_redraw()

func _draw() -> void:
    draw_rect(Rect2(0, 0, 160, 90), Color("15345f"), true)
    draw_circle(Vector2(80, 45), 28, Color("62d4ff"))
    draw_circle(Vector2(70, 39), 4, Color("081426"))
    draw_circle(Vector2(90, 39), 4, Color("081426"))
    draw_arc(Vector2(80, 48), 12, 0.2, PI - 0.2, 24, Color("081426"), 3)
