from eelengine import Eel, Canvas, mousePressed, mouseRelease, keyPressed
from eelengine.figure import setColor, drawRect, Font, Rectangle
import numpy as np
from enum import Enum
from collections import Counter

class Status(Enum):
    Nothing = 0
    Shown   = 1
    Flagged = 2
    Mined   = 3

BASE_COLOR = 0x00D111FF
RED_MULTI  = 0x20230400
OTHER_SUB  = 0x000F2F00

game = Eel('Eel Mines')

global MINEFIELD, NUMBERS, GRIDSIZE, GRIDSCREENSIZE, GRID, BUFFER
MINEFIELD = NUMBERS = GRID = BUFFER = None
GRIDSIZE = np.array([8, 8])
GRIDSCREENSIZE = None
MINEAMNT = 10

global SOLVED
SOLVED = None

HEIGHTMAP   = np.zeros(GRIDSIZE)
MAXHEIGHT   = 15
DELTAHEIGHT = 0.25

global GAMEFONT
GAMEFONT = None
number_list = []
symbol_list = {}
offsetvec = np.array([0, -1])

global LOST, WON, REDRAW, LOSEMINE
WON = LOST = False

LOSEMINE = None

def getNeighbors(array, i, j):
    return array[max(i-1, 0):i+2, max(j-1, 0):j+2]


def getPos(text, index, offset: float=0):
    return ((index)*GRIDSCREENSIZE) + GRIDSCREENSIZE//2 +\
            np.array([-text.width, text.height-text.bearing/2])//2 +\
            offset*offsetvec


def lose(mind):
    global LOST, LOSEMINE

    LOST = True
    LOSEMINE = mind

    for ind, val in np.ndenumerate(MINEFIELD):
        if val: GRID[ind] = Status.Mined


def expandZero(ind, nonzero=False):

    GRID[ind] = Status.Shown

    for _ind in np.ndindex(3, 3):
        x, y = npind = _ind - np.array([1, 1]) + ind

        if (x, y) == ind: continue

        if (npind < GRIDSIZE).all() and (npind >= 0).all():

            if GRID[x, y] is not Status.Shown and not MINEFIELD[x, y]:

                GRID[x, y] = Status.Shown
                HEIGHTMAP[x, y] = MAXHEIGHT

                if NUMBERS[x, y] == 0 or NUMBERS[x, y] == SOLVED[x, y]:
                    expandZero((x, y))

            elif nonzero and MINEFIELD[x, y] and GRID[x, y] is not Status.Flagged:
                lose((x, y))


@game.load
def initGrid(screen):
    global NUMBERS, GRIDSIZE, MINEFIELD, GRIDSCREENSIZE, GAMEFONT, GRID, REDRAW, BUFFER, SOLVED, WON, LOST, LOSEMINE

    ratio = MINEAMNT / GRIDSIZE.prod()

    MINEFIELD = np.fromfunction(
        np.vectorize(lambda i, j: int(np.random.rand() < ratio)),
        GRIDSIZE, dtype=int
    )

    NUMBERS = np.fromfunction(
        np.vectorize(lambda i, j: getNeighbors(MINEFIELD, i, j).sum()),
        GRIDSIZE, dtype=int
    )

    GRIDSCREENSIZE = screen.dimensions / GRIDSIZE

    GRID = np.zeros(GRIDSIZE, dtype=Status)
    SOLVED = np.zeros(GRIDSIZE)

    if GAMEFONT is None:
        GAMEFONT = Font("monoki/mononoki-Regular Nerd Font Complete.ttf")

        for i in range(9):
            number_list.append(GAMEFONT.text(0, 0, bytes(str(i), "utf-8")))

        symbol_list[Status.Mined] = GAMEFONT.text(0, 0, bytes("\uf1e2", "utf-8"))
        symbol_list[Status.Flagged] = GAMEFONT.text(0, 0, bytes("\uf73f", "utf-8"))

        BUFFER = Canvas(*screen.dimensions)
    
    REDRAW = True
    WON = LOST = False
    LOSEMINE = None


def drawTile(index, val, screen, offset: float=0):

        inverted = SOLVED[index] == NUMBERS[index]

        if GRID[index] is Status.Shown:

            if inverted:
                setColor(0x777777FF)

            else:
                setColor(BASE_COLOR + (val) * (RED_MULTI - OTHER_SUB))

        else: setColor(0x555555FF)

        drawRect(
            *(index * GRIDSCREENSIZE) + offset*offsetvec, *GRIDSCREENSIZE,
            fill=True, target=screen
        )

        setColor(1, 1, 1, 255)
        drawRect(fill=False, target=screen)

        if GRID[index] is Status.Shown:
            i = number_list[val]
            i.x, i.y = getPos(i, index, offset=offset)

            if inverted:
                i.setColor(BASE_COLOR + (val) * (RED_MULTI - OTHER_SUB))

            else: i.setColor(0xFFFFFFFF)

            i.drawTo(screen)


        elif GRID[index] in (Status.Mined, Status.Flagged):
            i = symbol_list[GRID[index]]
            i.x, i.y = getPos(i, index, offset=offset)

            if index == LOSEMINE:
                i.setColor(0xDD1111FF)

            else: i.setColor(0xFFFFFFFF)

            i.drawTo(screen)


@game.draw
def draw(screen):
    global REDRAW

    if REDRAW:

        # Reevaluate solveds

        BUFFER.clear()

        for index, val in np.ndenumerate(NUMBERS):

            SOLVED[index] = Counter(
                getNeighbors(GRID, *index).flatten()
            )[Status.Flagged]

            drawTile(index, val, BUFFER)

        REDRAW = False

    BUFFER.drawTo(screen)


@game.draw
def logic(screen):
    global LOST, WON, REDRAW, LOSEMINE

    x, y = npind = screen.mouse // GRIDSCREENSIZE
    mind = (int(x), int(y))

    if (npind < GRIDSIZE).all() and (npind >= 0).all():

        HEIGHTMAP[mind] = min(
            HEIGHTMAP[mind] + MAXHEIGHT / DELTAHEIGHT / (screen.fps or 60) * 3,
            MAXHEIGHT
        )

        for ind, val in np.ndenumerate(HEIGHTMAP):
            if val:
                drawTile(ind, NUMBERS[ind], screen, offset=val)
                HEIGHTMAP[ind] = max(
                    val - MAXHEIGHT / DELTAHEIGHT / (screen.fps or 60),
                    0
                )
        
        # Open board -----------------------------------------------------------
        REDRAW = True
        
        if not LOST:

            if mousePressed(0):

                if GRID[mind] is Status.Shown:
                    if NUMBERS[mind] == SOLVED[mind]:
                        expandZero(mind, True)

                else:
                    GRID[mind] = Status.Mined if MINEFIELD[mind] else Status.Shown
                    if NUMBERS[mind] == 0 or NUMBERS[mind] == SOLVED[mind]:
                        expandZero(mind)

                    if MINEFIELD[mind]:
                        lose(mind)

                mouseRelease(0)

            # Filtering --------------------------------------------------------
            elif mousePressed(1):

                if GRID[mind] in (Status.Nothing, 0):

                    GRID[mind] = Status.Flagged

                    WON = True
                    for ind, mine in np.ndenumerate(MINEFIELD):
                        if mine and GRID[ind] != Status.Flagged:
                            WON = False
                            break

                    if WON: print("You won!")

                elif GRID[mind] is Status.Flagged:
                    GRID[mind] = Status.Nothing

                mouseRelease(1)

            else: REDRAW = False

    if keyPressed('R'): initGrid(screen)
    elif keyPressed('Q'): screen.close()
    
    """
    for i in range(6):
        setColor(BASE_COLOR + (i) * (RED_MULTI - OTHER_SUB))
        drawRect(100*i, 100, 100, 100, fill=True, target=screen)
    """
    
game.run()