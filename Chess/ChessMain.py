"""
This is the main driver file. It will be responsible for handing user input and displaying the current GameState object.
"""

import pygame as p
from Chess import ChessEngine, SmartMoveFinder
from multiprocessing import Process, Queue

BOARD_WIDTH = BOARD_HEIGHT = 512 #400 is another option
MOVE_LOG_PANEL_WIDTH = 250
MOVE_LOG_PANEL_HEIGHT = BOARD_HEIGHT
DIMENSION = 8 #dimensions of a chess board are 8x8
SQ_SIZE = BOARD_HEIGHT // DIMENSION
MAX_FPS = 15 #for animations later on
IMAGES = {}

'''
Initialize a global dictionary of images. This will be called once in the main
'''
def loadImages():
    pieces = ['wp', 'wR', 'wN', 'wB', 'wK', 'wQ', 'bp', 'bR', 'bN', 'bB', 'bK', 'bQ']
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load("images/" + piece + ".png"), (SQ_SIZE, SQ_SIZE))
    #Note: we can access an image by saying 'IMAGES['wp']'

'''
The main driver. This will handle user input and updating the graphics
'''
def main():
    p.init()
    screen = p.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH, BOARD_HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    moveLogFont = p.font.SysFont("Arial", 14, False, False)
    gs = ChessEngine.GameState()
    validMoves = gs.getValidMoves()
    moveMade = False # flag variable for when a move is made
    animate = False # flag variable for when we should animate a move
    loadImages() #only do this once, before the while loop
    running = True
    sqSelected = () #no square is selected, keep track of the last click of the user (tuple: (row, col))
    playerClicks = [] #keep track of player clicks (two tuples: [(6, 4), (4, 4)]
    gameOver = False
    playerOne = True # If a human is playing white, then this will be True. If an AI is playing, then this will be False.
    playerTwo = False # Same as above but for black
    AIThinking = False
    moveFinderProcess = None
    moveUndone = False
    while running:
        humanTurn = (gs.whiteToMove and playerOne) or (not gs.whiteToMove and playerTwo)
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
            #mouse handler
            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver:
                    location = p.mouse.get_pos() #(x,y) location of mouse
                    col = location[0]//SQ_SIZE
                    row = location[1]//SQ_SIZE
                    if sqSelected == (row, col) or col >= 8: #the user clicked the same square twice or user clicked move log
                        sqSelected = () #deselect
                        playerClicks = [] #clear player clicks
                    else:
                        sqSelected = (row, col)
                        playerClicks.append(sqSelected) #append for both 1st and 2nd clicks
                    if len(playerClicks) == 2 and humanTurn: #after 2nd click
                        move = ChessEngine.Move(playerClicks[0], playerClicks[1], gs.board)
                        print(move.getChessNotation())
                        for i in range(len(validMoves)):
                            if move == validMoves[i]:
                                gs.makeMove(validMoves[i])
                                moveMade = True
                                animate = True
                                sqSelected = () #reset user clicks
                                playerClicks = []
                        if not moveMade:
                            playerCLicks = [sqSelected]
            # key handler
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z: # undo when 'z' is pressed
                    gs.undoMove()
                    sqSelected = ()
                    playerClicks = []
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                if e.key == p.K_r: # reset the board when 'r' is pressed
                    gs = ChessEngine.GameState()
                    validMoves = gs.getValidMoves()
                    sqSelected = ()
                    playerClicks= []
                    moveMade = False
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True

        #AI move finder
        if not gameOver and not humanTurn and not moveUndone:
            if not AIThinking:
                AIThinking = True
                print("thinking...")
                returnQueue = Queue() # used to pass data between threads
                moveFinderProcess = Process(target=SmartMoveFinder.findBestMove, args=(gs, validMoves, returnQueue))
                moveFinderProcess.start() # call findBestMove(gs, validMoves, returnQueue)

            if not moveFinderProcess.is_alive():
                print("done thinking")
                AIMove = returnQueue.get()
                if AIMove is None:
                    AIMove = SmartMoveFinder.findRandomMove(validMoves)
                gs.makeMove(AIMove)
                moveMade = True
                animate = True
                AIThinking = False

        if moveMade:
            if animate:
                animateMove(gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.getValidMoves()
            moveMade = False
            animate = False
            moveUndone = False

        drawGameState(screen, gs, validMoves, sqSelected, moveLogFont)

        if gs.checkmate or gs.stalemate:
            gameOver = True
            drawEndGameText(screen, 'Stalemate' if gs.stalemate else 'Black wins by checkmate' if gs.whiteToMove else 'White wins by checkmate')

        clock.tick(MAX_FPS)
        p.display.flip()

'''
Responsible for all the graphics within a current game state.
'''
def drawGameState(screen, gs, validMoves, sqSelected, moveLogFont):
    drawBoard(screen) #draw the squares on the board
    highlightSquare(screen, gs, validMoves, sqSelected)
    drawPieces(screen, gs.board) #draw pieces on top of those squares
    drawMoveLog(screen, gs, moveLogFont)

'''
Draw the squares on the board. The top left square is always light.
'''
def drawBoard(screen):
    global colors
    colors = [p.Color("white"), p.Color("gray")]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[((r+c) % 2)]
            p.draw.rect(screen, color, p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

'''
Highlight square selected and moves for piece selected
'''
def highlightSquare(screen, gs, validMoves, sqSelected):
    if sqSelected != ():
        r, c = sqSelected
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'): # sqSelected is a piece that can be moved
            #highlight selected square
            s = p.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(100) # transparency value -> 0 transparent; 255 opaque
            s.fill(p.Color('blue'))
            screen.blit(s, (c*SQ_SIZE, r*SQ_SIZE))
            #highlight moves from that square
            s.fill(p.Color('yellow'))
            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    screen.blit(s, (move.endCol*SQ_SIZE, move.endRow*SQ_SIZE))


'''
Draw the pieces on the board using the current GameState.board
'''
def drawPieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--": #not an empty square
                screen.blit(IMAGES[piece], p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

'''
Draws the move log
'''
def drawMoveLog(screen, gs, font):
    moveLogRect = p.Rect(BOARD_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, MOVE_LOG_PANEL_HEIGHT)
    p.draw.rect(screen, p.Color("black"), moveLogRect)
    moveLog = gs.moveLog
    moveTexts = []
    for i in range(0, len(moveLog), 2):
        moveString = str(i//2 + 1) + ". " + str(moveLog[i]) + "  "
        if i+1 < len(moveLog): # make sure black made a move
            moveString += str(moveLog[i+1]) + "  "
        moveTexts.append(moveString)

    movesPerRow = 3
    padding = 5
    lineSpacing = 2
    textY = padding
    for i in range(0, len(moveTexts), movesPerRow):
        text = ""
        for j in range(movesPerRow):
            if i + j < len(moveTexts):
                text += moveTexts[i+j]
        textObject = font.render(text, True, p.Color('white'))
        textLocation = moveLogRect.move(padding, textY)
        screen.blit(textObject, textLocation)
        textY += textObject.get_height() + lineSpacing


'''
Animating a move
'''
def animateMove(move, screen, board, clock):
    global colors
    dR = move.endRow - move.startRow
    dC = move.endCol - move.startCol
    framesPerSquare = 5  # frames to move one square
    frameCount = (abs(dR) + abs(dC)) * framesPerSquare

    for frame in range(frameCount + 1):
        # Interpolate the row and column of the moving piece for the current frame
        r = move.startRow + dR * frame / frameCount
        c = move.startCol + dC * frame / frameCount

        # Redraw the entire game state, excluding the moving piece
        drawBoard(screen)
        drawPieces(screen, board, skipRow=move.startRow, skipCol=move.startCol)

        # Redraw the square the moving piece is moving to
        color = colors[(move.endRow + move.endCol) % 2]
        endSquare = p.Rect(move.endCol * SQ_SIZE, move.endRow * SQ_SIZE, SQ_SIZE, SQ_SIZE)
        p.draw.rect(screen, color, endSquare)

        # If there is a captured piece, draw it onto the end square
        if move.pieceCaptured != '--':
            if move.isEnpassantMove:
                enPassantRow = move.endRow + 1 if move.pieceCaptured[0] == 'b' else move.endRow - 1
                endSquare = p.Rect(move.endCol * SQ_SIZE, enPassantRow * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            screen.blit(IMAGES[move.pieceCaptured], endSquare)

        # Draw the moving piece at its current position
        screen.blit(IMAGES[move.pieceMoved], p.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

        # Update the display and set the frame rate
        p.display.flip()
        clock.tick(60)

def drawPieces(screen, board, skipRow=None, skipCol=None):
    for r in range(len(board)):
        for c in range(len(board[r])):
            piece = board[r][c]
            if piece != "--":
                if r == skipRow and c == skipCol:
                    continue  # Skip the piece being animated
                screen.blit(IMAGES[piece], p.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

def drawEndGameText(screen, text):
    font = p.font.SysFont("Arial", 32, True, False)
    textObject = font.render(text, 0, p.Color('Gray'))
    textLocation = p.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH / 2 - textObject.get_width() / 2, BOARD_HEIGHT / 2 - textObject.get_height() / 2)
    screen.blit(textObject, textLocation)
    textObject = font.render(text, 0, p.Color("Black"))
    screen.blit(textObject, textLocation.move(2, 2))

if __name__ == "__main__":
    main()
