from subprocess import check_output
import re


class Results:
  issueCount = 0
  issueFiles = 0



ForRegex = re.compile("for \(.*\)$")
IfRegex = re.compile("if \(.*\)$")
ElseRegex = re.compile("else$")
ElseIfRegex = re.compile("else if \(.*\)$")

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'

hasIssue = False
issues = ""
noIssues = True

def setHasIssue(hi):
  global hasIssue
  hasIssue = hi

def getHasIssue():
  return hasIssue


def setNoIssues(hi):
  global noIssues
  noIssues = hi

def getNoIssues():
  return noIssues

def setIssues(iss):
  global issues
  issues = iss
  

def clearIssues():
  global issues
  issues = ""

def getIssues():
  return issues

def printBuf(string):
  setHasIssue(True)
  setNoIssues(False)
  setIssues(getIssues() + string + "\n")
  Results.issueCount +=1

def printIssues(fileName):
  if getHasIssue():
    print bcolors.FAIL +  fileName + bcolors.ENDC
    print getIssues()
    Results.issueFiles+=1
  setHasIssue(False)
  clearIssues()

def getBracketCount(line):
  count = 0
  quoteCount = 0
  for char in line:
    if char == '(' and  quoteCount %2 == 0: count +=1
    elif char == ')' and quoteCount %2 == 0: count -=1
    elif char == '"': quoteCount +=1
  return count

def isUnterminatedCtrl(line):
  bracketLevel = 0
  for i in xrange(len(line)):
    if line[i] == "(":
      bracketLevel += 1
    elif line[i] == ")":
      if bracketLevel == 1:
        #found the closing bracket. is there stuff after it?
        if i == len(line) -1:
          return True
        return False
      bracketLevel -= 1
  return True


def getIndent(string):
  for i in xrange(len(string)):
    if string[i] != ' ':
      return i
  return 0

bracket = 0
brace = 1

class IndentableStructure:
    def __init__(self, firstLine, closeBracketNeeded, level, bracketType):
      self.firstLine = firstLine
      self.closeBracketNeeded = closeBracketNeeded
      self.originalLevel = level
      if firstLine[0].isContinuation or (self.firstLine[-1].isContinuation and len(firstLine) == 2):
        self.level = level + 1
      else:
        self.level = level
      self.bracketType = bracketType


class Line:

  def checkElseIfIndentation(self):
    if "if(" in self.contents:
      printBuf("No space between 'if' and bracket:" + formatLine(self))
    elif "else if(" in self.contents:
      printBuf("No space between 'else if' and bracket:" + formatLine(self))

  def checkCommaSpacing(self):
    commaRegex = re.compile(",[A-Za-z]")
    if commaRegex.search(self.contents):
      printBuf("No space beteween ',' and next expression:" + formatLine(self))


  def checkTypeAnnotationSpacing(self):
    colonRegex1 = re.compile(":[A-Za-z](?!port)")
    if colonRegex1.search(self.contents):
      printBuf("No space after ':'" + formatLine(self))
    colonRegex2 = re.compile("\) :(?!:)(?!port)(?!mm)(?!ss)")
    if colonRegex2.search(self.contents):
      printBuf("Space between ')' and ':'" + formatLine(self))

  def __init__(self, contents, lineNumber, isComment):
    self.contents = contents.strip()
    self.fullContents = contents
    self.lineNumber = lineNumber

    if isComment:
      self.isComment = True
    else:
      self.isComment = False
    self.hasDef = False
    self.notTerminated = False
    self.isContinuation = False
    self.indent = getIndent(self.fullContents)
    self.endsIndentedBlock = False
    self.isEmpty = False
    self.startsIndentedBlock = False
    self.hasClass = False
    self.hasCase = False
    self.isImport = False
    self.hasOpenBracket = False
    self.hasCloseBracket = False
    self.hasIf = False
    self.hasElse = False
    self.hasCatch = False
    self.hasTry = False
    self.hasFinally = False

    bracketCount = getBracketCount(self.contents)

    #self.checkElseIfIndentation()
    #self.checkCommaSpacing()
    #self.checkTypeAnnotationSpacing()

    if self.contents == "":
      self.isEmpty = True
    elif self.contents.startswith("//") or self.contents.startswith("/*") or self.contents.startswith("*"):
      self.isComment = True
    else:
      if self.contents.startswith(".") or self.contents.startswith(":") or self.contents.startswith("extends") or self.contents.startswith("with"):
        self.isContinuation = True
      if "import " in self.contents:
        self.isImport = True
      if self.contents == "try":
        self.hasTry = True
      if "catch" in self.contents:
        self.hasCatch = True
      if self.contents == "finally":
        self.hasFinally = True
      if "if " in self.contents:
        self.hasIf = True
      if "else " in self.contents and not "else if" in self.contents:
        self.hasElse = True
      if "def " in self.contents:
        self.hasDef = True
      if "class " in self.contents:
        self.hasClass = True
      if "case " in self.contents and "case class" not in self.contents and "case object" not in self.contents:
        sandwiched = re.compile("\{.*case.*\}")
        if not sandwiched.search(self.contents):
          self.hasCase = True
      if bracketCount < 0:
        self.hasCloseBracket = True
      elif bracketCount > 0 and not self.hasDef and not self.hasClass:
        self.hasOpenBracket = True
      if "{" in self.contents:
        if "}" in self.contents:
          if self.contents.find("}") < self.contents.find("{"):
            self.startsIndentedBlock = True
        else:
          self.startsIndentedBlock = True
      if "}" in self.contents:
        if "{" in self.contents:
          if self.contents.find("}") < self.contents.find("{"):
            self.endsIndentedBlock = True
        else:
          self.endsIndentedBlock = True
      if (not self.startsIndentedBlock) and (self.contents.endswith(",") or self.contents.endswith(":") or self.contents.endswith(" with") or self.contents.endswith(" extends") or self.contents.endswith("+") or self.contents.endswith("&&") or self.contents.endswith("||") or (self.contents.endswith("=>") and not "{" in self.contents and not self.hasCase) or (ForRegex.match(self.contents) and isUnterminatedCtrl(line.contents)) or (IfRegex.match(self.contents) and isUnterminatedCtrl(line.contents)) or (ElseIfRegex.match(self.contents) and isUnterminatedCtrl(line.contents)) or (ElseRegex.match(self.contents) and isUnterminatedCtrl(line.contents))):
        self.notTerminated = True


    def trimPrefix(self, prefix):
      return Line(self.contents[len(prefix):], self.lineNumber)

class File:
  def __init__(self, fileName):
    self.fileName = fileName
    self.contents = open(fileName).read()
    self.lines = []
    splitLines = self.contents.split('\n')
    isComment = False
    for i in xrange(len(splitLines) -1):
      if "/*" in splitLines[i] and not "*/" in splitLines[i]:
        isComment = True
      elif "*/" in splitLines[i] and not "/*" in splitLines[i]:
        isComment = False
      self.lines.append(Line(splitLines[i], i + 1, isComment))

  def checkFormatting(self):
    self.checkForTabs()
    #self.checkImports()
    self.checkDocumentation()
    #self.checkEmptyLines()
    self.checkIndentation()
    #self.checkLineLength()

  def checkForTabs(self):
    for line in self.lines:
      if line.fullContents.startswith('\t'):
        printBuf("Line contains tab:" + str(len(line.fullContents)) + "):\n" + formatLine(line))

  def checkLineLength(self):
    for line in self.lines:
      if len(line.fullContents) > 100:
        printBuf("Line too long (" + str(len(line.fullContents)) + "):\n" + formatLine(line))

  # File imports should be in alphabetical order
  def checkImports(self):
    imports = [imp.trimPrefix("import ") for imp in self.lines if imp.contents.startswith("import ")]
    for i in xrange(len(imports) -1):
      if not imports[i].contents <= imports[i+1].contents:
        printBuf("Imports not sorted alphabetically:\n" + formatTwoLines(imports[i], imports[i+1]))
      prefix1 = imports[i].contents[:imports[i].contents.rindex(".")]
      prefix2 = imports[i+1].contents[:imports[i+1].contents.rindex(".")]
      if prefix1 == prefix2:
        printBuf("Two imports that should be combined:\n" + formatTwoLines(imports[i], imports[i+1]))

  def checkDocumentation(self):
    comments = [line for line in self.lines if line.contents.startswith("//")]
    for comment in comments:
      if not comment.contents.startswith("// ") and not comment.contents == "//":
        printBuf("No space between '//' and comment text:\n" + formatLine(comment))

    for i in xrange(len(self.lines)):
      line = self.lines[i]
      if line.contents.startswith("/*"):
        if line.contents == "/*" and self.lines[i+1].contents.startswith("*"):
          printBuf("Multi-line Scaladoc not properly started with /** :\n" + formatLine(line))
        elif line.contents.endswith("**/"):
          printBuf("Scaladoc not properly terminated with */:\n" + formatLine(line))
          if not line.contents.startswith("/** "):
            printBuf("No space between '/**' and Scaladoc text:\n" + formatLine(line))
      elif line.contents == ("**/"):
        printBuf("Scaladoc not properly terminated with */:\n" + formatLine(line))
      elif line.contents.startswith("*") and not line.contents.startswith("*/") and not line.contents == "*" and not line.contents.startswith("* "):
        printBuf("No space between '*' and Scaladoc text:\n" + formatLine(line))

  def checkEmptyLines(self):
    for i in xrange(len(self.lines) -1):
      if self.lines[i].contents == "":
        if self.lines[i+1].contents == "":
          printBuf("Two empty lines in a row:\n" + formatTwoLines(self.lines[i], self.lines[i+1]))
        elif self.lines[i+1].contents == "}":
          printBuf("Empty line before closing bracket:\n" + formatTwoLines(self.lines[i], self.lines[i+1]))
      elif (self.lines[i].contents.endswith("*/") or self.lines[i].contents.startswith("//")) and self.lines[i+1].contents == "":
        printBuf("Empty line after comment:\n" + formatTwoLines(self.lines[i], self.lines[i+1]))
      elif self.lines[i].contents.endswith("{") and self.lines[i+1].contents == "":
        printBuf("Empty line after opening bracket:\n" + formatTwoLines(self.lines[i], self.lines[i+1]))


  def checkIndentation(self):
    level = 0
    indentableStructures = []
    i = 0
    lines = self.lines
    while i < len(lines) -1:
      line = lines[i]
      if i > 0: prevline = lines[i-1] 
      else: prevline = Line("", 0, False)

      pushed = False

      if line.isComment:
        level = parseCommentLine(line, prevline, indentableStructures, level)
      elif not line.isEmpty:
        if line.endsIndentedBlock:
          level = parseCloseBlockLine(line, indentableStructures, level)
        else:
          parseNormalLine(prevline, line, level, indentableStructures)
        if line.hasIf or line.hasTry:
          lines = []
          lines.append(line)
          indentableStructures.append(IndentableStructure(lines, False, level, bracket))
        if line.hasElse or line.hasFinally:
          indentableStructures.pop()
        if line.hasDef:
          defLines = []
          i = collectDefLines(i, lines, defLines)
          if defLines: 
            level = parseDef(defLines, indentableStructures, level)
            pushed = True
        elif line.hasCase:
          if indentableStructures[-1].firstLine[0].hasCase:
            level = indentableStructures.pop().level
          level = parseCaseLine(line, indentableStructures, level)
          pushed = True
        elif line.hasClass:
          classLines = []
          i = collectClassLines(i, lines, classLines)
          if classLines: 
            level = parseClassLines(classLines, indentableStructures, level)
            pushed = True   
        elif line.startsIndentedBlock:
          level = parseStartsIndentedBlockLine(line, prevline, indentableStructures, level)
          pushed = True
        elif line.hasOpenBracket:
          lines = []
          lines.append(line)
          indentableStructures.append(IndentableStructure(lines, False, level, bracket))
          level +=1
          pushed = True
        elif line.contents.endswith("="): 
          lines = []
          lines.append(line)
          indentableStructures.append(IndentableStructure(lines, False, level, brace))
          level +=1

        if not line.notTerminated and not pushed:
          while indentableStructures and not indentableStructures[-1].closeBracketNeeded:
            if indentableStructures[-1].firstLine[0].hasCase:
              if line.hasCase:
                level = indentableStructures.pop().level
              else: break;
            else:
              level = indentableStructures.pop().level
      i+=1
      
     
def parseCommentLine (line, prevline, indentableStructures, level):
  if line.contents.startswith("*") and not startswithSpaces(line.fullContents, 2*level + 1):
    #indentation might be okay if last structure didn't need closing bracket
    last = None
    while indentableStructures and not indentableStructures[-1].closeBracketNeeded:
      last = indentableStructures.pop()

    if (not isIndentedForFormatting(prevline, line)) and (not last or not startswithSpaces(line.fullContents, 2*last.level)):
      printBuf("Incorrect indentation:" + formatLine(line))
    if last: level = last.level
  elif line.contents.startswith("/*") and not startswithSpaces(line.fullContents, 2*level):
    last = None
    while indentableStructures and not indentableStructures[-1].closeBracketNeeded:
      last = indentableStructures.pop()
    if (not isIndentedForFormatting(prevline, line)) and (not last or not startswithSpaces(line.fullContents, 2*last.level)):
      printBuf("Incorrect indentation:" + formatLine(line))
    if last: level = last.level
  return level

def parseCloseBlockLine(line, indentableStructures, level):
  p = False
  while indentableStructures and not indentableStructures[-1].closeBracketNeeded:
    if not "{" in line.contents:  #just added
      indentableStructures.pop()
    else: break
  opening = indentableStructures.pop()
  level = opening.level

  if not line.indent == 2 * level:
    if not (opening.firstLine[0].isImport or getBracketCount(opening.firstLine[0].contents) > 0):
      printBuf("Incorrect indentation for closing '}':" + formatLine(line))
  level = opening.originalLevel
  while indentableStructures and not indentableStructures[-1].closeBracketNeeded:
    if not "{" in line.contents and not indentableStructures[-1].firstLine[0].hasCase:  #just added
      level = indentableStructures.pop().originalLevel
    else: break
  return level

def parseCaseLine(line, indentableStructures, level):
  #if line.contents.endswith("=>") or line.notTerminated:
  lines = []
  lines.append(line)
  if "{" in line.contents:
    indentableStructures.append(IndentableStructure(lines, True, level, brace))
  else:
    indentableStructures.append(IndentableStructure(lines, False, level, brace))
  return level + 1

def parseStartsIndentedBlockLine(line, prevline, indentableStructures, level):
  lines = []
  lines.append(line)
  indentableStructures.append(IndentableStructure(lines, True, level, brace))
  if line.isContinuation or prevline.notTerminated:
    return level + 2
  return level + 1

def parseNormalLine(prevline, line, level, indentableStructures):
  if prevline.notTerminated or line.isContinuation: # should be indented
    if line.indent != (level + 1) * 2:
      printBuf("Bad indentation for multi-line:" + formatTwoLines(prevline, line))
  else: # should be indented, but there are some exceptions.
    if line.indent != level * 2:
      if len(indentableStructures) == 0 or not (line.indent == (level - 1) * 2 and (indentableStructures[-1].firstLine[0].hasIf or indentableStructures[-1].firstLine[0].hasTry or indentableStructures[-1].firstLine[0].hasCase)): # the indent is definitely wrong
        printBuf("Too much indentation:" + formatLine(line))
      else:
        if not(line.indent == (level -1)*2 and line.hasCase):
          printBuf("Too little indentation:" + formatLine(line))
  
def collectParamLines(index, lines, classLines):
  #looking for an unmatched ')'
  #if we find a { before a (, return (no params)
  bracketLevel = 0
  while True:
    for char in lines[index].contents:
      if char == '(': bracketLevel+=1
      elif char == '{' or char == "=":
        if bracketLevel == 0:
          classLines.append(lines[index])
          return index
      elif char == ')':
        if bracketLevel == 1:
          classLines.append(lines[index])
          return index
        else:
          bracketLevel -= 1
    classLines.append(lines[index])
    index +=1
  return index
    
def collectClassLines(index, lines, classLines):
  if lines[index].contents.endswith("}"): 
    return index

  #one line, has def
  if lines[index].contents.endswith("{"):
    classLines.append(lines[index])
    return index

  # one line, no def
  if not (lines[index].notTerminated or lines[index +1].isContinuation or lines[index].contents.endswith("(")) and not lines[index + 1].isContinuation and not isLastLineOfDef(lines[index].contents):
    return index

  index = collectParamLines(index, lines, classLines)
  if lines[index].contents.endswith("{"):   #the class def is over
    return index

  index +=1

  while not lines[index].contents.endswith("{") and (lines[index-1].notTerminated or lines[index-1].contents.endswith("(") or lines[index].isContinuation): #not isLastLineOfDef(lines[index].contents) and
    classLines.append(lines[index])
    index+=1

  if lines[index].contents.endswith("{"):
    classLines.append(lines[index])
  elif lines[index + 1].contents == "{":
    classLines.append(lines[index + 1])
    index +=1
  else:   # if the last line doesn't end with "=" or "{" or "(", then it's not a definition
    classLines[:] = []
  return index

def parseClassLines(classLines, indentableStructures, level):
  indentableStructures.append(IndentableStructure(classLines, True, level, brace))
  if classLines[0].isContinuation or (classLines[-1].isContinuation and len(classLines) == 2):
    return level + 2
  return level + 1

def parseDef(defLines, indentableStructures, level):
  lastLine = defLines[-1]
  # lines after the first and before the last must be indented
  for i in xrange(1, len(defLines) -1):
    if defLines[i].indent != 2*(level + 1):
      printBuf("Incorrect indentation in multiple-line def:" + formatLine(defLines[i]))
  # if there are two lines, the last should be indented
  if len(defLines) == 2:
    if lastLine.indent != 2*(level + 1):
      printBuf("Incorrect indentation in multiple-line def2:" + formatLine(lastLine))
  # if there are more than 2 lines, the last should be out-dented to the original level
  elif len(defLines) > 2:
    if lastLine.indent != 2*(level):
      printBuf("Incorrect indentation in multiple-line def3:" + formatLine(lastLine))
    # The last line should also start with "):"
    if not (lastLine.contents.startswith("):") or lastLine.contents.startswith(")(")):
      printBuf("Rtype in multi-line def not on newline" + formatLine(defLines[-1]))

  if "{" in lastLine.contents:
     indentableStructures.append(IndentableStructure(defLines, True, level, brace))

  # Insert the def onto the stack
  else:
    indentableStructures.append(IndentableStructure(defLines, False, level, brace))
  
  if defLines[0].isContinuation:
    return level + 2
  return level + 1

def collectDefLines(index, lines, defLines):

  if lines[index].contents.endswith("}"): 
    return index

  #one line, has def
  if isLastLineOfDef(lines[index].contents):
    defLines.append(lines[index])
    return index

  # one line, no def
  if not (lines[index].notTerminated or lines[index].contents.endswith("(") or lines[index].contents.endswith("=>")) and not lines[index + 1].isContinuation and not isLastLineOfDef(lines[index].contents):
    return index

  index = collectParamLines(index, lines, defLines)

  while not isLastLineOfDef(lines[index].contents) and (lines[index-1].notTerminated or lines[index-1].contents.endswith("(") or lines[index].isContinuation): #not isLastLineOfDef(lines[index].contents) and
    defLines.append(lines[index])
    index+=1
 
  if not (isLastLineOfDef(lines[index].contents) or lines[index].contents.endswith("(") or "{" in lines[index].contents):
    defLines[:] = []

  return index


def isIndentedForFormatting(prevline, line):
  return (not line.isComment) and (line.contents.startswith(".") or line.contents.startswith(":") or prevline.contents.endswith(",") or prevline.contents.endswith(":") or prevline.contents.endswith("("))

def isLastLineOfDef(line):
  #return ("=" in line and ")" in line) or line.endswith("=") or ("=" in line and "{" in line)
  return line.endswith("=") or line.endswith("{")

def lineShouldBeIndented(prevline, line):
  test1 = False
  if ForRegex.match(prevline.contents): test1 = True

  # if the prevline would have been matched as a function, we don't want the next line to be indented 2X
  if ("{" in prevline.contents and not "}" in prevline.contents) or ("{" in prevline.contents and prevline.contents.find("{") > prevline.contents.find("}")):
    return False


  if ForRegex.match(prevline.contents): return True
  test = (not line.isComment) and (line.contents.startswith(".") or line.contents.startswith(":") or prevline.contents.endswith(",") or prevline.contents.endswith(":") or prevline.contents.endswith("("))
  return (not line.isComment) and (line.contents.startswith(".") or line.contents.startswith(":") or prevline.contents.endswith(",") or prevline.contents.endswith(":") or prevline.contents.endswith("("))

def startswithSpaces(string, num):
  prefix = ""
  for i in range(0, num):
    prefix+= " "
  return string.startswith(prefix) and not string.startswith(prefix + " ")


def makeLines(l):
  string = ""
  for elem in l:
    string += "\t" + elem + "\n"
  return string


def getFileNames():
  gitOutput = check_output(["ls", "-R"]) #check_output(["git", "status"])
  #gitOutput = check_output(["git", "status"])
  
  lines = gitOutput.split("\n")
  parent = ""
  files = []
  for line in lines:
    line = line.lstrip()
    if line.endswith(":"):
      parent = line[len("./"):]
      parent = parent[:-1]
    elif line.endswith(".scala"):
      files.append(parent + "/" + line)
  return files

  #return [elem[len('\t'):] for elem in lines if elem.endswith(".scala")]

def formatLine(line1):
   return "\t" + bcolors.OKBLUE + str(line1.lineNumber) + bcolors.ENDC + "\t" + line1.contents

def formatTwoLines(line1, line2):
  return "\t" + bcolors.OKBLUE +  str(line1.lineNumber) + bcolors.ENDC  + "\t" + line1.contents + "\n\t" + bcolors.OKBLUE + str(line2.lineNumber) + bcolors.ENDC + "\t" + line2.contents


def getAndClipLinesStartingWith(lines, prefix):
  return [elem.trimPrefix(prefix) for elem in lines if elem.startswith(prefix)]

fileNames = getFileNames()
searchedFiles = 0
for fileName in fileNames:
  _file = None
  
  try:
    _file = File(fileName)
  except: IOError

  if _file:
    _file.checkFormatting()
    printIssues(fileName)
    searchedFiles +=1
  

print "Searched " + str(searchedFiles) + " files for style."
if Results.issueCount == 0:
  print bcolors.OKGREEN + "Looks good!" + bcolors.ENDC
elif Results.issueCount == 1:
  print bcolors.WARNING + "Found " + str(Results.issueCount) + " issue in " + str(Results.issueFiles) + " files." + bcolors.ENDC
else:
  print bcolors.WARNING + "Found " + str(Results.issueCount) + " issues in " + str(Results.issueFiles) + " files." + bcolors.ENDC
