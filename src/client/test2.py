import pygame
import numpy as np
from math import *


def rotations(point, angle):
    def rotation_zw():
        return np.matrix([
            [cos(angle), -sin(angle), 0, 0],
            [sin(angle), cos(angle), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ])

    def rotation_yw():
        return np.matrix([
            [cos(angle), 0, -sin(angle), 0],
            [0, 1, 0, 0],
            [sin(angle), 0, cos(angle), 0],
            [0, 0, 0, 1]
        ])

    def rotation_yz():
        return np.matrix([
            [cos(angle), 0, 0, -sin(angle)],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [sin(angle), 0, 0, cos(angle)]
        ])

    def rotation_xw():
        return np.matrix([
            [1, 0, 0, 0],
            [0, cos(angle), -sin(angle), 0],
            [0, sin(angle), cos(angle), 0],
            [0, 0, 0, 1]
        ])

    def rotation_xz():
        return np.matrix([
            [1, 0, 0, 0],
            [0, cos(angle), 0, -sin(angle)],
            [0, 0, 1, 0],
            [0, sin(angle), 0, cos(angle)]
        ])

    def rotation_xy():
        return np.matrix([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, cos(angle), -sin(angle)],
            [0, 0, sin(angle), cos(angle)]
        ])

    result = point.reshape((4, 1))
    for rot in [rotation_zw(), rotation_yw(), rotation_xw(), rotation_xz()]:
        result = np.dot(rot, result)
    return result


WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))

scale = 150

circle_pos = [WIDTH / 2, HEIGHT / 2]  # x, y

angle = 0

points = [[1, 1, 1, 1], [1, 1, 1, -1], [1, 1, -1, 1], [1, 1, -1, -1],
          [1, -1, 1, 1], [1, -1, 1, -1], [1, -1, -1, 1], [1, -1, -1, -1],
          [-1, 1, 1, 1], [-1, 1, 1, -1], [-1, 1, -1, 1], [-1, 1, -1, -1],
          [-1, -1, 1, 1], [-1, -1, 1, -1], [-1, -1, -1, 1], [-1, -1, -1, -1]]
points = list(map(np.matrix, points))

projection3d_matrix = np.matrix([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0]
])
projection2d_matrix = np.matrix([
    [1, 0, 0],
    [0, 1, 0]
])


def connect_points(i, j, points):
    pygame.draw.line(screen, BLACK, (points[i][0], points[i][1]), (points[j][0], points[j][1]))


clock = pygame.time.Clock()
while True:

    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()

    angle += 0.01

    screen.fill(WHITE)

    projected_points = [None for _ in points]
    i = 0
    for point in points:
        rotated3d = rotations(point, angle)
        projected3d = np.dot(projection3d_matrix, rotated3d.reshape(4, 1))
        projected2d = np.dot(projection2d_matrix, projected3d.reshape(3, 1))

        x = int(projected2d[0][0] * scale) + circle_pos[0]
        y = int(projected2d[1][0] * scale) + circle_pos[1]

        projected_points[i] = [x, y]
        pygame.draw.circle(screen, RED, (x, y), 5)
        i += 1

    lines = [
        (0, 1), (2, 3), (0, 2), (1, 3),
        (4, 5), (6, 7), (4, 6), (5, 7),
        (8, 9), (10, 11), (8, 10), (9, 11),
        (12, 13), (14, 15), (12, 14), (13, 15),

        (0, 4), (1, 5), (2, 6), (3, 7),
        (8, 12), (9, 13), (10, 14), (11, 15),

        (0, 8), (1, 9), (2, 10), (3, 11),
        (4, 12), (5, 13), (6, 14), (7, 15)
    ]
    for i, j in lines:
        connect_points(i, j, projected_points)

    pygame.display.update()
