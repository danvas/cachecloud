"""
*** Cache Cloud ***
Version 0.8
by Daniel Vasquez 
Updated: March 22, 2011
Email: dan@heylight.com
Web: heylight.com

Description:
Python script that creates Maya Particle Disk Cache (PDC) files from a sequence of point cloud data, and also gives you the choice of importing a single point cloud. It could be useful with all the open source data being released from Kinect hacks or 3D scanners. You can start by playing around with Radiohead's House Of Cards data: http://code.google.com/p/radiohead/downloads/list

Tags: 
point cloud, maya, PDC, particle disk cache, python, data visualization, kinect, 3D scanner

Notes:
1) The point cloud data source files should be named serially (with numbers in suffix), with padding. Currently it doesn't take numbered prefixes very well. That said, you might have to rename/serialize your source files appropriately - for example, "frame001.txt" or "dynamite01.csv". Here's a good program to do so on a Mac: http://www.pathossoftware.com/Rename/Rename.html
2) For a point cloud animation, you can select a range of ordered files or a single file. If one file is selected, all files in the animation sequence will be cached.
3) This version accepts CSV and TXT files containing arrays* in the form of:

    integer, float, float, float 
    OR
    float, float, float, integer 
    OR
    float, float, float
    
    *per line, comma-separated or whitespace-separated. Try another form of arrays at your own risk.
4) There's a bug that makes Maya crash when you play the animation past the last frame of the cache. The script automatically sets it to the appropriate timeslider range, so in the meantime just avoid changing the timeslider playback range.  
5) For a single point cloud, the extra attribute selected is added automatically; for animated point clouds, you need to manually add the selected attribute after closing Cache Cloud.
6) Be aware that this script creates a new cache folder and a CacheCloud_history.txt file in your Maya workspace (in the particles directory).
7) This script has only been tested in 64-bit Maya 2011 running on OSX, but I don't see why it wouldn't work in Windows. The UI prompts are called from Maya commands.

License: 
The Cache Cloud script is made available under the Creative Commons Attribution-Noncommercial-Share Alike 3.0 License.
This license lets you remix, tweak, and build upon Cache Cloud non-commercially, and although your new works must also acknowledge Daniel Vasquez (heylight.com) and be non-commercial, you donÕt have to license your derivative works on the same terms.
For more information on this license, read http://creativecommons.org/licenses/by-nc/3.0/legalcode and http://creativecommons.org/licenses/by-nc/3.0/

Things to do:
¥ Minimize code redundancy.
¥ GUI for making particle and attributes more customizable. 
¥ Give option for modifying the point cloud data. For example, remove all repeated points, ease translation of position by a factor, or scale up/down.
¥ Currently this script creates a default particle disk cache using mc.dynExport, which might not be necessary. 
¥ Figure out the bug that's making Maya crash (see notes above). 
¥ Allow flexibility with particleId.
¥ Add nParticles option, which would result in creating Maya Cache Files. (Might be better to write a separate script for this.)

"""
#----------------------------------------------------------------------------------------------------------------------------
### Imports
import os                             
from struct import *
import maya.cmds as mc
import datetime
# from binascii import hexlify # To represent binary data in hexadecimal. Could be useful in debugging.

#----------------------------------------------------------------------------------------------------------------------------
### Define functions
# Checking the numerical contents of a string without changing the type
def checkNum(strContent):
    t = strContent.strip()
    if t.isdigit(): 
        return 'integer'
    else: 
        return 'float'

# For data structure (i.e. form of array) analysis
def arrayForm(contentSampling):
    sample = contentSampling[len(contentSampling)//2] # Arbitrary point (median index, in this case) is used for analysis. (This analysis could probably be better done with other statistical methods.)
    if sample.count(',') > 1: # Analyze comma-separated values. 
        if len(sample.split(',')) == 4:
            pointData = sample.split(',')
            if checkNum(pointData[0]) == 'integer':
                return 'commas',acceptableArrayforms['i3fC'], 4
            elif checkNum(pointData[0]) == 'float': 
                return 'commas', acceptableArrayforms['3fiC'], 4
            else:
                return None,acceptableArrayforms['u'], None
        elif len(sample.split(',')) == 3:
            pointData = sample.split(',')
            if checkNum(pointData[0]) == 'float': 
                return 'commas',acceptableArrayforms['3fC'], 3
            else:
                return None,acceptableArrayforms['u'], None
    elif sample.count(' ') > 1: # Analyze space-separated values
        if len(sample.split(' ')) == 4:
            pointData = sample.split(' ')
            if checkNum(pointData[0]) == 'integer':
                return 'spaces',acceptableArrayforms['i3f'], 4
            elif checkNum(pointData[0]) == 'float': 
                return 'spaces',acceptableArrayforms['3fi'], 4
            else:
                return None,acceptableArrayforms['u'], None
        elif len(sample.split(' ')) == 3:
            pointData = sample.split(' ')
            if checkNum(pointData[0]) == 'float': 
                return 'spaces',acceptableArrayforms['3f'], 3
            else:
                return None,acceptableArrayforms['u'], None
    else:
        return None,acceptableArrayforms['u'], None

def makePointcoords(arrayFormResult):  
    if point == '':
        content.remove('')
    elif arrayDelimiter == 'commas':
        pointData = point.split(',')
        if arrayFormResult == acceptableArrayforms['i3fC']:
            pointPos = float(pointData[1]), float(pointData[2]), float(pointData[3])
            pointCoords.append(pointPos)
            extraAttrValues.append(float(pointData[0]))  
        elif arrayFormResult == acceptableArrayforms['3fiC']: 
            pointPos = float(pointData[0]), float(pointData[1]), float(pointData[2])
            pointCoords.append(pointPos)
            extraAttrValues.append(float(pointData[3])) 
        elif arrayFormResult == acceptableArrayforms['3fC']: 
            pointPos = float(pointData[0]), float(pointData[1]), float(pointData[2])
            pointCoords.append(pointPos)
    elif arrayDelimiter == 'spaces':
        pointData = point.split(' ')
        if arrayFormResult == acceptableArrayforms['i3f']:
            pointPos = float(pointData[1]), float(pointData[2]), float(pointData[3])
            pointCoords.append(pointPos)
            extraAttrValues.append(float(pointData[0]))
        elif arrayFormResult == acceptableArrayforms['3fi']: 
            pointPos = float(pointData[0]), float(pointData[1]), float(pointData[2])
            pointCoords.append(pointPos)
            extraAttrValues.append(float(pointData[3])) 
        elif arrayFormResult == acceptableArrayforms['3f']: 
            pointPos = float(pointData[0]), float(pointData[1]), float(pointData[2])
            pointCoords.append(pointPos)
            
# Function for setting the PDC file incremental value according to frame rate
def pdcfileStep(frameRate):
    if frameRate == 'pal': 
        return 240
    elif frameRate == 'ntsc': 
        return 200
    elif frameRate == 'film': 
        return 250
    elif frameRate == 'palf': 
        return 120
    elif frameRate == 'ntscf': 
        return 100
    elif frameRate == 'show': 
        return 125
    else: 
        return 200
        
def exitPrompt():
    surePrompt = mc.confirmDialog( icn = 'warning', title='Leaving Cache Cloud...', message='Sure you want to stop here?', button=['Go Back','Stop'], defaultButton='Go Back', cancelButton='Stop', dismissString='Stop' )
    if surePrompt == 'Go Back':
        return True
    else:
        print("*** Goodbye.")
        #historyLog.write('{0}\n\n\n'.format((datetime.datetime.now()).strftime("SESSIONEND\tNo particles created. User exited: %Y-%m-%d %H:%M:%S")))
        return False
### Initiate-------------------------------------------------------------------------------------------------------------------
versionNum = '0.8.4'
print('*** Welcome to Cache Cloud version {0} ***'.format(versionNum))
# Prepare the directory for particle disk cache (PDC) files
projectrootDir = str(mc.workspace(q=1,rootDirectory=1)) 
particlesDir =  projectrootDir + 'particles/'
if os.path.isfile(particlesDir + 'CacheCloud_history.txt'): # Record session in history log
    historyLog = open(particlesDir + 'CacheCloud_history.txt', 'a') # If file exists, append write
else:
    historyLog = open(particlesDir + 'CacheCloud_history.txt', 'w') # If file doesn't exist, create new and write
    historyLog.write('{0} Cache Cloud {1} {2}\n'.format('*'*6, versionNum,'*'*6 )) # Write title and general info
    historyLog.write('Written by Daniel Vasquez\nEmail: dan@heylight.com\n\n')
    historyLog.write('History log:\n\n')
acceptableArrayforms = {'i3fC': 'int, float, float, float',
                            '3fiC': 'float, float, float, int',
                            '3fC': 'float, float, float', 
                            'i3f': 'int float float float',
                            '3fi': 'float float float int',
                            '3f':'float float float',
                            'u': 'unknown'}
pointCoords = []  
extraAttrValues = []
cleanPrompt = None
surePrompt = True
### Choose import type and select file(s)
while surePrompt:
    importChoice = mc.confirmDialog(icn='information',title='Welcome to Cache Cloud!',message="Create PDC files from a point cloud animation or\nimport point cloud single.",button=['Animation', 'Single', 'Cancel'],defaultButton='Animation',cancelButton='Cancel',dismissString='Cancel')
    if importChoice == 'Animation':
        sourceFiles = mc.fileDialog2(fm=4, ds = 2, okc = 'Select', cap = 'Select the first file in the point cloud animation or a range of files') 
        try:
            sourceFiles.sort() # Sort files in order - important for timeslider range
        except: AttributeError
        if sourceFiles == None:
            surePrompt = exitPrompt()
        else:
            break   
    elif importChoice == 'Single':
        sourceFiles = mc.fileDialog2(fm=1, ds = 2, okc = 'Select', cap = 'Select a point cloud data file')
        if sourceFiles == None:
            surePrompt = exitPrompt()
        else:
            break   
    else:
        surePrompt = exitPrompt()    
if importChoice == 'Animation':
    while surePrompt:
        result = mc.promptDialog(title='New scene',message='Name the scene for your point cloud animation:',button=['OK', 'Cancel'],defaultButton='OK',cancelButton='Cancel',dismissString='Cancel')
        if result == 'OK':
            sceneName = mc.promptDialog(query=True, text=True)
            break
        elif result == 'Cancel':
            surePrompt = exitPrompt()
    while surePrompt:
        timeUnits = {'25 fps': 'pal', '60 fps': 'ntscf', '30 fps': 'ntsc', '50 fps': 'palf', '24 fps': 'film', '15 fps': 'game', '48 fps': 'show', 'Other': 'Next', 'Not sure': 'ntsc'}
        frameRate = timeUnits[mc.confirmDialog(icn = 'question', title='Set time unit',message = 'choose frame rate:', button=['30 fps','25 fps', 'Other'],defaultButton='30 fps',cancelButton='30 fps',dismissString='30 fps')] # Choose a frame rate. To do: Get rid of text field.
        if frameRate != 'Next':
            print('*** Frame rate has been set to {0}.'.format(frameRate))
        elif frameRate == 'Next':
            frameRate = timeUnits[mc.confirmDialog(icn = 'question', title='Set time unit',message = 'choose frame rate:', button=['24 fps', '60 fps', '50 fps', '48 fps', 'Not sure'],defaultButton='Not sure',cancelButton='Not sure',dismissString='Not sure')] # Choose a frame rate. To do: Get rid of text field.
            print('*** Frame rate has been set to {0}.'.format(frameRate))
        # Give save current scene options
        try:
            mc.file(new=1)
            mc.file(rename=sceneName)
            mc.file(save=1, type='mayaAscii') # Only saves as .ma file
            mc.currentUnit(time = frameRate) # 
            break
        except RuntimeError:
            savePrompt = mc.confirmDialog(icn = 'warning',title='Create new scene:', message='Save and close the current scene?', button=['Save','Save As','Don\'t Save', 'Cancel'], defaultButton='Save', cancelButton='Cancel', dismissString='Cancel' )
            if savePrompt == 'Save':
                nameSavedscene = str(mc.file(q=1,sceneName=1, shortName=1))
                mc.file(save=1)
                print('*** The following was saved and closed: "{0}" '.format(nameSavedscene))
                mc.file(new=1)
                mc.file(rename=sceneName)
                mc.file(save=1, type='mayaAscii')
                mc.currentUnit(time = frameRate)
                print('*** New scene "{0}.ma" was created. '.format(sceneName))
                break
            elif savePrompt == 'Save As':
                chosenFile = mc.fileDialog2()[0]
                mc.file(rename = chosenFile)
                mc.file(save=1)  # To do: When replacing an .ma file with a .mb file. Unable to reopen it after. // Error: Error reading file. //  
                print('*** The following was saved and closed: "{0}" '.format(chosenFile))
                mc.file(new=1)
                mc.file(rename=sceneName)
                mc.file(save=1, type='mayaAscii')
                mc.currentUnit(time = frameRate)
                print('*** New scene "{0}.ma" was created. '.format(sceneName))
                break
            elif savePrompt == 'Don\'t Save': 
                mc.file(new=1, f=1)
                mc.file(rename=sceneName)
                mc.file(save=1, type='mayaAscii')
                mc.currentUnit(time = frameRate)
                print('*** New scene "{0}.ma" was created. '.format(sceneName))
                break
            elif savePrompt == 'Cancel':
                surePrompt = exitPrompt()
    #---------------------------------------------------------------------------------------------- -------------------     
    ### Prepare the directory for particle disk cache (PDC) files
    sceneNameWithExt = str(mc.file(q=1,sceneName=1, shortName=1))
    sceneName = sceneNameWithExt.split('.')[0] # Re-assign sceneName with current scene name, just to be sure. (Also good to have for script updates.)
    cacheoutputDir = particlesDir + sceneName + '/'
    #print("particlesDir = '{0}' \ncacheoutputDir = '{1}' \nsceneName = '{2}'".format(particlesDir, cacheoutputDir, sceneName))
    while surePrompt:
        if os.path.exists(particlesDir): # If particles folder exists. 
            createDirPrompt = mc.confirmDialog( title='Prepare folder for PDC files:', message='The following folder will be created in the particles directory of your project:\n /{0} '.format(sceneName), button=['Okay','Stop'], defaultButton='Okay', cancelButton='Stop', dismissString='Stop' )
            if createDirPrompt == 'Okay':
                if os.path.exists(cacheoutputDir):
                    print('*** The folder /{0} already exists and was not overwritten. '.format(sceneName))
                    break # If cache folder with same name already exists, skip folder creation.
                os.makedirs(cacheoutputDir)
                print('*** The folder /{0} was created in your project workspace. '.format(sceneName))
                break
            else:
                surePrompt = exitPrompt()
        else:
            createDirPrompt = mc.confirmDialog( title='Preparing folders for PDC files:', message='The following folders will be created in the directory of the current project:\n /{0}/{1} '.format('particles',sceneName), button=['Okay','Stop'], defaultButton='Okay', cancelButton='Stop', dismissString='Stop' )
            if createDirPrompt == 'Okay':
                os.makedirs(cacheoutputDir)
                print('*** The folders /{0} was created in your project workspace. '.format(cacheoutputDir))
                break
            else: # Exit prompt
                surePrompt = exitPrompt()
    ### Create particle object at first frame and make initial cache
    while surePrompt:
        particlenamePrompt = mc.promptDialog(title='Create particle',message='Name the particle object:',button=['OK', 'Cancel'],defaultButton='OK',cancelButton='Cancel',dismissString='Cancel')
        if particlenamePrompt == 'OK':
            particlesName = mc.promptDialog(query=True, text=True)
            if particlesName == '':
                particlenamePrompt = mc.confirmDialog( icn = 'warning', title='Careful...', message='No particle name was entered', button=['Try Again'], defaultButton='Try Again', cancelButton='Try Again', dismissString='Try Again' )
            else:
                mc.particle(name=particlesName)
                mc.file(save=1)
                # Get shape name of particle object. This name will be used for naming the PDC files.
                pdcBasename = [n for n in mc.ls(shapes=1) if n.startswith(''.join(i for i in particlesName if not i.isdigit()))][0] # Get particle shape name. The following command is much faster: mc.particle(q=1,n=1)
                print('*** Particle "{0}" was created. '.format(particlesName))
                break
        elif particlenamePrompt == 'Cancel':
            surePrompt = exitPrompt()
    while surePrompt:
        ### Make a list of the source files and analyze data structure to clean up
        #Extract information from the first file
        if len(sourceFiles) == 1: # If only one file was selected, use all relevant files in the directory. Otherwise, keep sourceFiles as is.
            namePrefix = ( ''.join(i for i in os.path.split(sourceFiles[0])[1] if not i.isdigit()) ).split('.')[0] # Get the prefix name
            firstFrame = int(''.join(i for i in os.path.split(sourceFiles[0])[1] if i.isdigit()))
            #sourcefileDir = os.path.split(sourceFiles[0])[0] # This is just in case someone gets confused with the expression below to re-assign sourceFiles. (No idea how I managed this one. Basically, it makes a list of all the files in the remaining sequence with the same prefix name.)
            sourceFiles = [(os.path.split(sourceFiles[0])[0] + '/' + f)  # Selected directory + f
                             for f in os.listdir(os.path.split(sourceFiles[0])[0]) # Make list: For f in [all files in selected directory]
                             if f.startswith(namePrefix) and # Only if f starts with the same namePrefix
                             os.path.isfile(os.path.split(sourceFiles[0])[0] + '/' + f) and # and if f is an actual file 
                             firstFrame <= int(''.join(i for i in f if i.isdigit())) ] # and if f is greater than the selected file. 
            inFile = open(str(sourceFiles[0]), 'r') # Make a list of its contents (i.e. assign content)
            fileContent = inFile.read()
            content = fileContent.split("\n") 
            inFile.close()
            del fileContent # Free up memory 
            print('*** Single file in the data sequence was selected. Using all files in same sequence.')
            # Clean up some points
            arrayDelimiter = arrayForm(content)[0]
            arrayFormResult = arrayForm(content)[1]
            [makePointcoords(arrayFormResult) for point in content]# Function that collects pointCoords data
            zerosCount = len([x for x in pointCoords if sum(x) ==0]) # Get the offset of every zero-value point  
            if zerosCount > 0:     
                cleanPrompt = mc.confirmDialog(icn = 'warning', title='Clean Up', message='After looking at the data in "{1}", {0} points were found to have zero-value.\nRemove all zero-value points?'.format(zerosCount, os.path.split(sourceFiles[0])[1]), button=['Remove','Keep'], defaultButton='Keep', cancelButton='Keep', dismissString='Keep' )
                if cleanPrompt == 'Remove':
                    print('*** {0} zero-value points will be removed.'.format(zerosCount))
                else:
                    print('*** There are zero-values that will not be removed.')
            sourceDir= os.path.split(sourceFiles[0])[0] + '/'
        elif len(sourceFiles) > 1: # Keep sourceFiles as is.
            namePrefix = ( ''.join(i for i in os.path.split(sourceFiles[0])[1] if not i.isdigit()) ).split('.')[0] # Get the prefix name
            print('*** A range of files in the data sequence was selected.') # If a range of files was selected, use those files only
            inFile = open(str(sourceFiles[0]), 'r') # Make a list of its contents (i.e. assign content)
            fileContent = inFile.read()
            content = fileContent.split("\n") 
            inFile.close()
            del fileContent # Free up memory
             # Clean up some points
            arrayDelimiter = arrayForm(content)[0]
            arrayFormResult = arrayForm(content)[1]
            [makePointcoords(arrayFormResult) for point in content]# Function that collects pointCoords data
            zerosCount = len([x for x in pointCoords if sum(x) ==0])  # Get the offset of every zero-value point   
            if zerosCount > 0:  
                cleanPrompt = mc.confirmDialog(icn = 'warning', title='Clean Up', message='After looking at the data in "{1}", {0} points were found to have zero-value.\nRemove all zero-value points?'.format(zerosCount, os.path.split(sourceFiles[0])[1]), button=['Remove','Keep'], defaultButton='Keep', cancelButton='Keep', dismissString='Keep' )
                if cleanPrompt == 'Remove':
                    print('*** Zero-value points will be removed.')
                else:
                    print('*** There are zero-values that will not be removed.')
            sourceDir= os.path.split(sourceFiles[0])[0] + '/'
            firstFrame = int(''.join(i for i in os.path.split(sourceFiles[0])[1]if i.isdigit()))
        fileExt = '.' + ( ''.join(i for i in os.path.split(sourceFiles[0])[1] if not i.isdigit()) ).split('.')[1]    # File extension
        ### Set up timeslider depending on number of source files (i.e. sourceFiles). (This section is questionable and might not even be necessary.)
        framesCount = len(sourceFiles)  
        startFrame = mc.playbackOptions(e=1, ast= firstFrame)
        endFrame = mc.playbackOptions(e=1, animationEndTime = firstFrame + framesCount - 1)
        mc.playbackOptions(e=1, min=startFrame)
        mc.playbackOptions(e=1, max=endFrame)  # The minus 2 buffer is a temporary fix to the issue of Maya crashing at the last frame.
        mc.currentTime(startFrame)
        # Create a default particle disk cache (which will be overwritten)
        mc.dynExport( particlesName, path = sceneName,  f = 'cache', mnf = firstFrame, mxf = endFrame, oup = 0)
    #-----------------------------------------------------------------------------------------------------------------     
        ### This is where it all the magic happens! Writing the PDC files in binary...
        # Assign default header values for writing binary PDC file
        fileType = 'PDC '
        formatVersion = 1
        byteOrder = 1
        extra1 = 0
        extra2 = 0 
        dataType = {'Integer': 0, 
                    'Integer Array': 1,
                    'Double': 2,
                    'Double Array': 3,
                    'Vector': 4, 
                    'Vector Array': 5}
        # This is important for naming the PDC files in a specific incremental value
        pdcNameIncrementsValue = pdcfileStep(frameRate)
        pdcIncrements = firstFrame * pdcNameIncrementsValue
        offset = -1 # This is if the arrayLength is 3
        writtenPDCCount = 0
        arrayDelimiter = arrayForm(content)[0]
        arrayFormResult = arrayForm(content)[1]
        if arrayForm(content)[2] == 4:
            print('*** The following form of array was detected: {0}'.format(arrayForm(content)[1]))
            extraAttr = mc.confirmDialog( title='Extra attribute', message='There was an extra integer value detected in the arrays. Assign it to an attribute?', button=['radiusPP','opacityPP', 'rotationPP', 'SKIP' ], defaultButton='SKIP', cancelButton='SKIP', dismissString='SKIP' )
            extraAttrValues = []
            [makePointcoords(arrayFormResult) for point in content]# Function to collects extraAttrValues data
            avgAttrvalues = sum(extraAttrValues)/len(extraAttrValues)
            maxAttrValue = max(extraAttrValues)
            #minAttrValue = min(extraAttrValues)
            if extraAttr == 'SKIP': # If no attribute was chosen , make the arrayLength = 3
                arrayLength = 3
            else:
                while surePrompt:
                    scalefactorPrompt = mc.promptDialog(title='Scale attribute',text = '{0}'.format(str(1/maxAttrValue)),message='The highest value of {0} is {2}. The average value is {1:.2f}.\n Scale it by:'.format(extraAttr,avgAttrvalues, maxAttrValue),button=['OK', 'Cancel'],defaultButton='OK',cancelButton='Cancel',dismissString='Cancel')
                    if scalefactorPrompt == 'OK':
                        extraScalefactor = mc.promptDialog(query=True, text=True)
                        if extraScalefactor == '':
                            mc.confirmDialog( icn = 'warning', title='Careful...', message='No scale value was entered', button=['Try Again'], defaultButton='Try Again', cancelButton='Try Again', dismissString='Try Again' )
                        else:
                            print('*** A multiplication factor of {0} will be applied to {1} values. '.format(extraScalefactor, extraAttr))
                            break
                    elif scalefactorPrompt == 'Cancel':
                        surePrompt = exitPrompt()
                print('*** The extra integer value has been assigned to the attribute: {0}.'.format(extraAttr))  
                arrayLength = arrayForm(content)[2] # This should reference to 4
        else:
            arrayLength = arrayForm(content)[2] # This should reference to 3
            print('*** The following form of array was detected: {0}'.format(arrayForm(content)[1]))
        print('*** Beginning to write PDC files. This may take some time...')
        print(datetime.datetime.now()).strftime("*** Started: %Y-%m-%d %H:%M:%S")
        historyLog.write('{0}\n'.format((datetime.datetime.now()).strftime("SESSIONSTART    Started creating PDC files: %Y-%m-%d %H:%M:%S")))
        historyLog.write('INPUT\t{0} files ({3}) with root name "{1}" from {2}\n'.format(str(len(sourceFiles)),namePrefix,sourceDir,fileExt))
    #-----------------------------------------------------------------------------------------------------------------     
        # Loop for each file to make a PDC file.
        for sourcefile in sourceFiles:
            inFile = open(str(sourcefile), 'r')
            fileContent = inFile.read()
            inFile.close()
            content = fileContent.split("\n") # Note: content object gets re-assigned here
            del fileContent # Free up memory
            pointCoords = []  
            extraAttrValues = []
            
            for point in content: 
                makePointcoords(arrayFormResult) # Function that collects pointCoords data
                
            particleIds = range(len(pointCoords)) 
            if cleanPrompt == 'Remove': # Clean up zero-point values if user chose 'Remove' in cleanPrompt above
                particleIds = [pointCoords.index(x) for x in pointCoords if sum(x) !=0] # Collect offsets that correspond to nonzero-value points to use as particleIds
                #print('///{1} points were removed from {0}'.format(os.path.split(sourcefile)[1],len([pointCoords.index(x) for x in pointCoords if sum(x) ==0]))) 
                historyLog.write('OUTPUT\t{1} points were removed from {0}\n'.format(os.path.split(sourcefile)[1],len([x for x in pointCoords if sum(x) == 0]))) 
                pointCoords = [x for x in pointCoords if sum(x) !=0] # Filter out all zero-value pointsparticlesTotal = len(pointCoords)
            if arrayLength == 4:
                extraAttrValuesR = []
                [extraAttrValuesR.append(extraAttrValues[i]*float(extraScalefactor)) for i in particleIds]
                extraAttrValues = extraAttrValuesR
                
            attributes = ['position','particleId']
            attrValues = [pointCoords, particleIds]
            particlesTotal = len(pointCoords)
            if arrayLength == 4:
                offset = 0
                attributes = [str(extraAttr)] + attributes
                attrValues = [extraAttrValues] + attrValues  # The extra attribute values are collected in the makePointcoords() function
                recordsValues1 = (len(attributes[0]),
                              attributes[0],
                              dataType['Double Array'])
                for i in extraAttrValues: 
                    recordsValues1 += float(i),
                    
                recordsFormExtra = ' i{0}si{1}d'.format(str(len(attributes[0])),
                                                    str(len(extraAttrValues)) )
            # Assign records values
            recordsValues2 = (len(attributes[1 + offset]),
                              attributes[1 + offset],
                              dataType['Vector Array'])
            scaleFactor = 1
            for coord in pointCoords:
                recordsValues2 += coord[0]*scaleFactor,coord[1]*scaleFactor,coord[2]*scaleFactor
            
            recordsValues3 = (len(attributes[2 + offset]),
                              attributes[2 + offset],
                              dataType['Double Array'])
            for i in particleIds: 
                recordsValues3 += float(i),
            headerForm = '>4sii2iii'  
            attributesTotal = len(attributes)       
            headerValues = (fileType,
                            formatVersion,
                            byteOrder,
                            extra1,
                            extra2,
                            particlesTotal,
                            attributesTotal)   
            recordsForm = ' i{0}si{1}d i{2}si{3}d'.format(str(len(attributes[1 + offset])),
                                                          str(3* particlesTotal),
                                                          str(len(attributes[2 + offset])),
                                                          str(len(particleIds))  )
            # Pack the binary data into the PDC files
            if arrayLength == 4:
                form = Struct(headerForm + recordsFormExtra + recordsForm)
                allValues = headerValues + recordsValues1 + recordsValues2 + recordsValues3
            elif arrayLength == 3:
                form = Struct(headerForm + recordsForm)
                allValues = headerValues + recordsValues2 + recordsValues3
            packedData = form.pack(*allValues)
            fileName = pdcBasename + '.' + str(pdcIncrements) + ".pdc"
            outputPDCfile = open(cacheoutputDir + fileName, 'wb')
            outputPDCfile.write(packedData)
            outputPDCfile.close()
            #historyLog.write('OUTPUT    Source file {0}: {1}\n'.format(os.path.split(sourcefile)[1], cacheoutputDir + fileName) )
            print('// Writing PDC file from {0}: {1}'.format(os.path.split(sourcefile)[1], cacheoutputDir + fileName) )
            pdcIncrements += pdcNameIncrementsValue     # Add value according to frameRate
            writtenPDCCount  += 1
        break    
    if surePrompt:
        historyLog.write('OUTPUT\t{0} PDC files have been written to {1}\n'.format(str(writtenPDCCount),cacheoutputDir))
        #historyLog.write('HEADER\tType = {0}\nHEADER\tFormat version = {1}\nHEADER\tByte order = {2}\nHEADER\tExtra1 = {3}\nHEADER\tExtra2 = {4}\n'.format(fileType,formatVersion, byteOrder,extra1,extra2))
        historyLog.write('RECORDS\tTotal points = {0}\nRECORDS\tAttributes assigned = {1}\n'.format(str(particlesTotal),attributes))
        historyLog.write('{0}\n\n\n'.format((datetime.datetime.now()).strftime("SESSIONEND\tPDC files completed: %Y-%m-%d %H:%M:%S")))
        print('*** Your particle disk cache has been created. Thanks for using Cache Cloud!\n\n')
        finalPrompt = mc.confirmDialog(title='Done.', message='Your particle disk cache has been created.\nThanks for using Cache Cloud!', button=['Close','Heylight.com'], defaultButton='Close', cancelButton='Close', dismissString='Close' )
        if finalPrompt == 'Close':
            historyLog.close()
            mc.currentTime(startFrame)
            #mc.addAttr (-ln goalWeight0PP0 -dt doubleArray drtfhShape
        else:
            historyLog.close()
            mc.currentTime(startFrame)
            import webbrowser 
            webbrowser.open('http://folio.heylight.com/#953120/Info')
        surePrompt = False
    elif surePrompt == False:
        finalPrompt = mc.confirmDialog(title='Exit', message='Your particle disk cache has not been created. Thanks for using Cache Cloud anyway!', button=['Close'], defaultButton='Close', cancelButton='Close', dismissString='Close' )    

### If importing a single point cloud ---------------------------------------------------------------------------------------------------------------- 
elif importChoice == 'Single':
    inFile = open(str(sourceFiles[0]), 'r')
    fileContent = inFile.read()
    inFile.close()
    content = fileContent.split("\n") # Note: content object gets re-assigned here
    del fileContent # Free up memory
    arrayDelimiter = arrayForm(content)[0]
    arrayFormResult = arrayForm(content)[1]
    if arrayFormResult == 'unknown':
        abortPrompt = mc.confirmDialog(title='Aborting', message='An {0} form of array was detected. Aborting Cache Cloud.'.format(arrayForm(content)[1]), button=['Close'], defaultButton='Close', cancelButton='Close', dismissString='Close' )    
        print('*** An {0} form of array was detected. Aborted Cache Cloud.'.format(arrayForm(content)[1]))
        surePrompt = False
    print(datetime.datetime.now()).strftime("// Started: %Y-%m-%d %H:%M:%S")
    historyLog.write('{0}\n'.format((datetime.datetime.now()).strftime("SESSIONSTART    Created single point cloud: %Y-%m-%d %H:%M:%S")))
    for point in content: 
        makePointcoords(arrayFormResult) # Function that collects pointCoords and extraAttrValues data
    particleIds = range(len(pointCoords)) 
    #if surePrompt: # I think this surePrompt is totally unnecessary. Remove later, and test.
    zerosCount = len([x for x in pointCoords if sum(x) ==0])  # Get the offset of every zero-value point   
    if zerosCount > 0:  
        cleanPrompt = mc.confirmDialog(icn = 'warning', title='Clean Up', message='After looking at the data in "{1}", {0} points were found to have zero-value.\nRemove all zero-value points?'.format(zerosCount, os.path.split(sourceFiles[0])[1]), button=['Remove','Keep'], defaultButton='Keep', cancelButton='Keep', dismissString='Keep' )
        if cleanPrompt == 'Remove':
            print('*** Zero-value points will be removed.')
        else:
            print('*** There are zero-values that will not be removed.')
    historyLog.write('INPUT\tSingle point-cloud data file: {0}\n'.format(str(sourceFiles[0])))
    if arrayForm(content)[2] == 4:
        print('*** The following form of array was detected: {0}'.format(arrayForm(content)[1]))
        extraAttr = mc.confirmDialog( title='Extra attribute', message='There was an extra integer value detected in the arrays. Assign it to an attribute?', button=['radiusPP','opacityPP', 'mass', 'SKIP' ], defaultButton='SKIP', cancelButton='SKIP', dismissString='SKIP' )
        maxAttrValue = max(extraAttrValues)
        avgAttrvalues = sum(extraAttrValues)/len(extraAttrValues)
        if extraAttr == 'SKIP': # If no attribute was chosen , make the arrayLength = 3
            arrayLength = 3
        else:
            while surePrompt:
                scalefactorPrompt = mc.promptDialog(title='Scale attribute',text = '{0}'.format(str(1/maxAttrValue)),message='The highest value of {0} is {2}. The average value is {1:.2f}.\n Scale it by:'.format(extraAttr,avgAttrvalues, maxAttrValue),button=['OK', 'Cancel'],defaultButton='OK',cancelButton='Cancel',dismissString='Cancel')
                if scalefactorPrompt == 'OK':
                    extraScalefactor = mc.promptDialog(query=True, text=True)
                    if extraScalefactor == '':
                        mc.confirmDialog( icn = 'warning', title='Careful...', message='No scale value was entered', button=['Try Again'], defaultButton='Try Again', cancelButton='Try Again', dismissString='Try Again' )
                    else:
                        print('*** A multiplication factor of {0} will be applied to {1} values. '.format(extraScalefactor, extraAttr))
                        break
                elif scalefactorPrompt == 'Cancel':
                    surePrompt = exitPrompt()
            print('*** The extra integer value has been assigned to the attribute: {0}.'.format(extraAttr))  
            arrayLength = arrayForm(content)[2] # This should reference to 4
    else:
        arrayLength = arrayForm(content)[2] # This should reference to 3
        print('*** The following form of array was detected: {0}'.format(arrayForm(content)[1]))
    if cleanPrompt == 'Remove': # Clean up zero-point values if user chose 'Remove' in cleanPrompt above
        particleIds = [pointCoords.index(x) for x in pointCoords if sum(x) !=0] # Collect offsets that correspond to nonzero-value points to use as particleIds
        #print('///{1} points were removed from {0}'.format(os.path.split(sourcefile)[1],len([pointCoords.index(x) for x in pointCoords if sum(x) ==0]))) 
        historyLog.write('OUTPUT\t{1} points were removed from data in {0}\n'.format(os.path.split(sourceFiles[0])[1],len([x for x in pointCoords if sum(x) == 0]))) 
        pointCoords = [x for x in pointCoords if sum(x) !=0] # Filter out all zero-value pointsparticlesTotal = len(pointCoords)
    mc.particle(n= os.path.split(sourceFiles[0])[1].split('.')[0]+'particle',position = pointCoords)# create particles with same name as source file
    attributes = ['position','particleId']
    if arrayLength == 4:
        attributes = [str(extraAttr)] + attributes
        extraAttrValuesR = []
        [extraAttrValuesR.append(extraAttrValues[i]*float(extraScalefactor)) for i in particleIds]
        extraAttrValues = extraAttrValuesR
        mc.addAttr(mc.particle(q=1,n=1),ln=extraAttr, dt='doubleArray') # Add the extraAttr to the particle object
        mc.addAttr(mc.particle(q=1,n=1),ln=extraAttr+'0', dt='doubleArray') # Add the extraAttr to the particle object
        [mc.particle(e=1, at = extraAttr, id=i, fv = v) for i, v in enumerate(extraAttrValues)] # Edit the values corresponding to extraAttrValues for each particle
    historyLog.write('OUTPUT\tTotal points = {0}\nOUTPUT\tAttributes assigned = {1}\n'.format(str(len(pointCoords)),attributes))
    historyLog.write('OUTPUT\tNo cache was created for single frame\n')    
    historyLog.write('{0}\n\n\n'.format((datetime.datetime.now()).strftime("SESSIONEND\tImport completed: %Y-%m-%d %H:%M:%S")))
    print(datetime.datetime.now()).strftime("// Completed: %Y-%m-%d %H:%M:%S")
    print('*** Your point cloud has been imported. Thanks for using Cache Cloud!\n')
    finalPrompt = mc.confirmDialog(title='Done.', message='Your particles have been created.\nThanks for using Cache Cloud!', button=['Close','Heylight.com'], defaultButton='Close', cancelButton='Close', dismissString='Close' )
    if finalPrompt == 'Close':
        historyLog.close()
    elif finalPrompt == 'Heylight.com':
        historyLog.close()
        import webbrowser 
        webbrowser.open('http://folio.heylight.com/#953120/Info')
    else: pass
elif surePrompt == False:
    finalPrompt = mc.confirmDialog(title='Exit', message='Thanks for using Cache Cloud anyway!', button=['Close'], defaultButton='Close', cancelButton='Close', dismissString='Close' )     
