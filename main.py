__author__ = 'Karol Scipniak and Dominik Lochynski'

import numpy as np
import sys

sys.path.append("c:\Python27\DLLs")
import cv2
from sklearn.cluster import KMeans
from midiutil.MidiFile import MIDIFile


def importAndPrepareImage(imagePath):
    img = cv2.imread(imagePath)
    ret, gray = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY)
    return gray


def createFiveline(img):
    edges = cv2.Canny(img, 50, 150, apertureSize=3)

    ys = list()
    minLineLength = 5
    maxLineGap = 30

    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 70, minLineLength, maxLineGap)
    for line in lines:
        for x1, y1, x2, y2 in line:
            if (abs(y1 - y2 < 4)):
                innerlist = list()
                innerlist.append((y1 + y2) / 2)
                ys.append(innerlist)

    kmeans = KMeans(init='k-means++', n_clusters=5, n_init=10)
    kmeans.fit(np.asarray(ys))

    fiveline = list()
    for innerlist in kmeans.cluster_centers_:
        fiveline.append(innerlist[0])

    fiveline.sort()
    return fiveline


def createChecks(fiveline):
    checks = list()
    dist = abs(fiveline[1] - fiveline[0])

    for line in fiveline:
        checks.append(int(line - (dist / 4)))
        checks.append(int(line + (dist / 4)))

    checks.sort()
    checks.reverse()
    return checks


def createBarsCoordinates(img, fiveline, checks):
    barsBegins = list();
    barsEnds = list();
    bars = list()

    height, width = img.shape[:2]

    barsFlag = False
    leftCounter = 0
    rightCounter = 0
    for x in range(width):
        gen = (i for i in range(int(fiveline[0] + 2), int(fiveline[4])) if img[i, x][0] == 0)

        c = 0
        for i in gen:
            c += 1

        if barsFlag is False and c == abs(int(fiveline[0] + 2) - int(fiveline[4])):

            for l in range(x - 5, x - 2):
                for y in checks:
                    if img[y, l][0] == 0:
                        # gray[y, x] = [255, 0, 0]
                        leftCounter += 1

            barsBegins.append(x)
            barsFlag = True

        if barsFlag is True and not (c == abs(int(fiveline[0] + 2) - int(fiveline[4]))):

            for r in range(x + 2, x + 5):
                for y in checks:
                    if img[y, r][0] == 0:
                        # gray[y, x] = [255, 0, 0]
                        rightCounter += 1
            barsEnds.append(x)
            barsFlag = False

            if leftCounter > 0 or rightCounter > 0:
                # barsEnds.
                barsEnds.pop(len(barsEnds) - 1)
                barsBegins.pop(len(barsBegins) - 1)
            leftCounter = 0
            rightCounter = 0

    print
    print barsBegins
    print barsEnds
    print

    return barsBegins, barsEnds


def findAllTunes(noteValues, img, checks, barsBegins, barsEnds):
    iTunes = list()
    for bar in range(len(barsBegins) - 1):
        barLength = abs(barsEnds[bar] - barsBegins[bar + 1]) - 2
        pointsX = list()
        pointsY = list()
        for x in range(barsEnds[bar] + 1, barsBegins[bar + 1] - 1):
            for y in checks:
                if img[y, x][0] == 0:
                    # gray[y, x] = [255, 0, 0]
                    innerlistX = list()
                    innerlistX.append(x)
                    innerlistY = list()
                    innerlistY.append(y)
                    pointsX.append(innerlistX)
                    pointsY.append(innerlistY)

        kmeans2 = KMeans(init='k-means++', n_clusters=4, n_init=10)
        kmeans2.fit(np.asarray(pointsX), np.asarray(pointsY))

        notes = list()
        kmeans2.cluster_centers_.sort(axis=0)
        if abs(kmeans2.cluster_centers_[3, 0] - kmeans2.cluster_centers_[0, 0]) < 2:
            continue

        # print kmeans2.cluster_centers_
        notes.append(kmeans2.cluster_centers_[0, 0])

        for cc in range(1, kmeans2.cluster_centers_.shape[0]):
            if abs(kmeans2.cluster_centers_[cc, 0] - notes[len(notes) - 1]) > (
                        abs(barsEnds[bar] - barsBegins[bar + 1]) - 2) / 6:
                notes.append(kmeans2.cluster_centers_[cc, 0])
            else:
                notes[len(notes) - 1] = (notes[len(notes) - 1] + kmeans2.cluster_centers_[cc, 0]) / 2

        print notes

        notePointsList = list()
        for note in notes:
            notePoints = 0
            for x in range(int(note - barLength / 14), int(note + barLength / 14)):
                for y in checks:
                    if img[y, x][0] == 0:
                        # gray[y, x] = [255, 0, 0]
                        notePoints += 1

            print notePoints
            notePointsList.append(notePoints)

        for note in notes:
            noteLength = 0
            if len(notes) == 1:
                noteLength = 4
            elif len(notes) == 2:
                noteLength = 2;
            elif len(notes) == 3:
                if notes.index(note) == notePointsList.index(min(notePointsList)):
                    noteLength = 2
                else:
                    noteLength = 1
            elif len(notes) == 4:
                noteLength = 1

            noteHeight = 0
            for l in range(int(note - 20), int(note + 20)):
                ntCounter = 0
                for y in checks:
                    if img[y, l][0] == 0:
                        ntCounter += 1
                if ntCounter == 2:
                    for y in checks:
                        if img[y, l][0] == 0:
                            noteHeight = noteValues[checks.index(y)]
                            break;

                    break

            iTunes.append((noteLength, noteHeight))

        print
    print iTunes
    return iTunes


def exportTunesToMIDIFile(iTunes, outputPath):
    MyMIDI = MIDIFile(1)

    track = 0
    time = 0

    MyMIDI.addTrackName(track, time, "Sample Track")
    MyMIDI.addTempo(track, time, 240)

    track = 0
    channel = 0
    pitch = 60
    time = 0
    duration = 1
    volume = 100

    time = 0
    for noteLength, noteHeight in iTunes:
        MyMIDI.addNote(track, channel, noteHeight, time, noteLength, volume)
        time += duration * noteLength

    binfile = open(outputPath, 'wb')
    MyMIDI.writeFile(binfile)
    binfile.close()


def processImageFindAllNotesAndExportToMIDI(noteValues, imgPath):
    img = importAndPrepareImage(imgPath)

    height, width = img.shape[:2]

    fiveline = createFiveline(img)

    checks = createChecks(fiveline)

    barsBegins, barsEnds = createBarsCoordinates(img, fiveline, checks)

    iTunes = findAllTunes(noteValues, img, checks, barsBegins, barsEnds)

    exportTunesToMIDIFile(iTunes, imgPath + ".mid")


def main():
    noteValues = (52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83)

    processImageFindAllNotesAndExportToMIDI(noteValues, 'nuty1.png')
    processImageFindAllNotesAndExportToMIDI(noteValues, 'sheet3.png')


if __name__ == '__main__':
    main()

