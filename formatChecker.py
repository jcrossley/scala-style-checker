from subprocess import check_output
from subprocess import check_call
import re
import sys
import os




class Utils:
  @staticmethod
  def isAnyOf(elem, options):
    for option in options:
      if elem == option:
        return True
    return False

class Results:
  issueCount = 0
  issueFiles = 0
  fileHasIssue = False;
  noIssues = True
  issues = ""


class SType:
  DEF = "def"
  CLASS = "class"

def matchTokens(ctx):
  if ctx.curToken() == "def":
    return SType.DEF
  elif ctx.curToken() == "class":
    return SType.CLASS
 # else:
 #   print ctx.curToken()

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'

class Parser:
  @staticmethod
  def tokenize(string):
    lines = []
    splitLines = string.split('\n')
    for i in xrange(len(splitLines)):
      tokens = ['\n']
      token = ""
      c = 0
      while c < len(splitLines[i]):
        if Utils.isAnyOf(splitLines[i][c], [' ', ',', ':', '{', '}', '[', ']', '(', ')', '=', '.', '>']):
          if splitLines[i][c] == '=' and c < len(splitLines[i]) -1 and splitLines[i][c+1] == '>':
            tokens.append("=>")
            c+=2
            continue
          if token:
            tokens.append(token)
          tokens.append(splitLines[i][c])
          token = ""
        else:
          token += splitLines[i][c]
        c+=1
      if token:
        tokens.append(token)
      lines.append(Line(splitLines[i], tokens, i+1))
      #print tokens
    return lines

class Ctx:
  def __init__(self, lines):
    self.lines = lines
    self.lineIndex = 0
    self.tokenIndex = 0
    if self.lines:
      self.done =  False
    else:
      self.done = True

  def curToken(self):
    if self.lines[self.lineIndex].length == 0:
      return '\n'
    else:
      return self.lines[self.lineIndex].tokens[self.tokenIndex]

  def position(self):
    return (self.lineIndex, self.tokenIndex)

  def setPosition(self, position):
    self.lineIndex = position[0]
    self.tokenIndex = position[1]

  def incr(self):
    if self.done:
      return
    if self.tokenIndex == self.lines[self.lineIndex].length -1 \
       or self.lines[self.lineIndex].length == 0:
      self.tokenIndex = 0;
      if self.lineIndex == len(self.lines)-1:
        self.done = True
      else:
        self.lineIndex+=1
    else:
      self.tokenIndex+=1

class Line:
  def __init__(self, contents, tokens, lineNumber):
    self.contents = contents
    self.tokens = tokens
    self.lineNumber = lineNumber
    self.length = len(self.tokens)

class File:
  def __init__(self, fileName):
    self.fileName = fileName
    self.contents = open(fileName).read()
    self.issues = ""
    self.hasIssue = False

  def printIssues(self):
    print bcolors.FAIL +  self.fileName + bcolors.ENDC
    print self.issues

  def record(self, issue):
    self.hasIssue = True
    Results.noIssues = False
    self.issues += issue + "\n"
    Results.issueCount +=1

  def checkFormatting(self):
    lines = Parser.tokenize(self.contents)
    ctx = Ctx(lines)
    while not ctx.done:
      sType = matchTokens(ctx)

      result = True

      if sType == SType.DEF: result = parseDef(ctx)
      elif sType == SType.CLASS: result = parseClass(ctx)
      if result == False:
        self.record(formatLine(ctx.lines[ctx.lineIndex]))
      ctx.incr()
    return

keyWords = {"def", "class", "extends", "with", "\n"}

class DFA:
  def __init__(self, name, transitions, startState, acceptStates, subTriggers = {}):
    self.transitions = transitions
    self.startState = startState
    self.acceptStates = acceptStates
    self.subTriggers = subTriggers
    self.name = name

  def run(self, ctx):
    currentState = self.startState
    wordRegex = re.compile("^[A-Za-z0-9\*]*$")
    visitedAcceptStates = []

    while not ctx.done:
      token = ctx.curToken()
      if wordRegex.match(token) and not token in keyWords:
          token = '_'
      if (currentState, token) in self.subTriggers.keys():
        if not self.subTriggers[(currentState, token)][0].run(ctx): return False
        currentState =  self.subTriggers[(currentState, token)][1]
        continue
      if (currentState, token) not in self.transitions.keys():
        if currentState in self.acceptStates:
          return True
        if visitedAcceptStates:
          #print "trying to backtrack!"
          visitedAcceptState = visitedAcceptStates.pop()
          currentState = visitedAcceptState[0]
          ctx.setPosition(visitedAcceptState[1])
          return True
        else:
          #print "visitedAcceptStates:" + str(visitedAcceptStates)
          print "DFA error in:" + self.name + ", Current State:" + str(currentState) + ", token:" + token + "K"
          return False
      #print ctx.curToken(),
      if currentState in self.acceptStates:
        #print "In accept state!"
        visitedAcceptStates.append((currentState, ctx.position()))
        #print visitedAcceptStates
      currentState = self.transitions[(currentState, token)];
      ctx.incr()
    return True


class DFAs:
  word = '_'


  #value DFA
  tName = dict()
  tName[(0, word)] = 1
  tName[(1, '.')] = 0
  nameDFA = DFA("value", tName, 0, {1})

  tFunctionValue = dict()
  tFunctionValue[(1, ' ')] = 2
  tFunctionValue[(2, '=>')] = 3
  tFunctionValue[(3, ' ')] = 4
  stFunctionValue = dict()
  stFunctionValue[(4, word)] = (nameDFA, 5)
  functionValueDFA = DFA("function value", tFunctionValue, 0, {5}, stFunctionValue)

  #type parameter DFA
  tTypeParam = dict()
  tTypeParam[(0, '[')] = 1
  tTypeParam[(2, ']')] = 5
  tTypeParam[2, ','] = 3
  tTypeParam[2, ' '] = 4
  tTypeParam[4, '<'] = 6
  tTypeParam[6, ':'] = 7
  tTypeParam[7, ' '] = 8
  tTypeParam[3, ' '] = 1
  stTypeParam = dict()
  typeParamDFA = DFA("type parameter", tTypeParam, 0, {5}, stTypeParam)

  tSimpleType = dict()
  stSimpleType = dict()
  stSimpleType[(1, '[')] = (typeParamDFA, 2)
  stSimpleType[(0, word)] = (nameDFA, 1)
  simpleTypeDFA = DFA("simple type", tSimpleType, 0, {1, 2, 3}, stSimpleType)

  #type DFA
  tType = dict()
  tType[(2, ' ')] = 3
  tType[(3, '=>')] = 4
  tType[(4, ' ')] = 5

  stType = dict()
  stType[(1, '[')] = (typeParamDFA, 2)
  stType[(0, word)] = (nameDFA, 1)
  typeDFA = DFA("type", tType, 0, {1, 2, 7}, stType)
  stType[(5, word)] = (simpleTypeDFA, 7)
  stType[(5, '(')] = (simpleTypeDFA, 7)
  stTypeParam[(1, word)] = (typeDFA, 2)
  stTypeParam[(1, '(')] = (typeDFA, 2)
  stTypeParam[(8, word)] = (typeDFA, 2)
  stTypeParam[(8, '(')] = (typeDFA, 2)
  stSimpleType[(0, '(')] = (typeDFA, 3)


  #function type param DFA
  tFunctionTypeParam = dict()
  tFunctionTypeParam[(0, word)] = 1
  stFunctionTypeParam = dict()
  stFunctionTypeParam[(1, '[')] = (typeParamDFA, 4)
  functionTypeParamDFA = DFA("function type (parameter)", tFunctionTypeParam, 0, {1, 4}, stFunctionTypeParam)

  #function type DFA
  tFunctionType = dict()
  tFunctionType[(0, '(')] = 1
  tFunctionType[(2, ',')] = 3
  tFunctionType[(3, ' ')] = 1
  tFunctionType[(2, ')')] = 4
  tFunctionType[(4, ' ')] = 5
  tFunctionType[(5, '=>')] = 6
  tFunctionType[(6, ' ')] = 7
  stFunctionType = dict()
  stFunctionType[(1, word)] = (functionTypeParamDFA, 2)
  stFunctionType[(7, word)] = (typeDFA, 8)
  stFunctionType[(7, '(')] = (typeDFA, 8)
  functionTypeDFA = DFA("function type", tFunctionType, 0, {8}, stFunctionType)
  stType[(0, '(')] = (functionTypeDFA, 7)

  #type annotation DFA
  t = dict()
  t[(0, ':')] = 1
  t[(1, ' ')] = 2
  st = dict()
  st[(2, word)] = (typeDFA, 3)
  st[(2, '(')] = (typeDFA, 3)
  typeAnnotationDFA = DFA("type annotation", t, 0, {3}, st)

  #parameterItem DFA
  t = dict()
  t[(0, word)] = 1
  t[(2, ' ')] = 3
  t[(3, '=')] = 4
  t[(4, ' ')] = 5
  t[(4, '\n')] = 7
  t[(7, ' ')] = 8
  t[(8, ' ')] = 5
  st = dict()
  st[1, ':'] = (typeAnnotationDFA, 2)
  st[(5, word)] = (nameDFA, 6)
  st[(5, '(')] = (functionValueDFA, 6)
  parameterItemDFA = DFA("parameter item", t, 0, {2, 6}, st)


  #single-line parameter list
  t = dict()
  t[(1, ',')] = 2
  t[(2, ' ')] = 0
  st = dict()
  st[(0, word)] = (parameterItemDFA, 1)
  paramsSingleLine = DFA("params single line", t, 0, {0, 1}, st)


  #multi-line parameter list
  t = dict()
  t[(0, '\n')] = 1
  t[(1, ' ')] = 2
  t[(2, ' ')] = 3
  t[(4, ',')] = 0
  st = dict()
  st[(3, word)] = (parameterItemDFA, 4)
  paramsMultiLine = DFA("params multi-line", t, 0, {0, 4}, st)

  #parameter list DFA
  t = dict()
  t[(0, '(')] = 1
  t[(1, ')')] = 4
  t[(2, ')')] = 4
  t[(3, '\n')] = 5
  t[(5, ')')] = 4
  st = dict()
  st[(1, word)] = (paramsSingleLine, 2)
  st[(1, '\n')] = (paramsMultiLine, 3)
  paramListDFA = DFA("params list", t, 0, {4}, st)
  stFunctionValue[(0, '(')] = (paramListDFA, 1)


  #extendsDFA
  t = dict()
  t[(0, 'extends')] = 1
  t[(1, ' ')] = 2
  t[(3, ' ')] = 4
  t[(4, 'with')] = 1
  st = dict()
  st[(2, word)] = (typeDFA, 3)
  st[(2, '(')] = (typeDFA, 3)
  extendsDFA = DFA("extends", t, 0, {3}, st)


  #def DFA
  t = dict()
  t[(0, 'def')] = 1
  t[(1, ' ')] = 2
  t[(2, word)] = 3
  t[(4, ' ')] = 6
  t[(6, '=')] = 7
  t[(6, '{')] = 7
  st = dict()
  st[(3, '[')] = (typeParamDFA, 3)
  st[(3, '(')] = (paramListDFA, 4)
  st[(4, ':')] = (typeAnnotationDFA, 5)
  defDFA = DFA("def", t, 0, {5, 7}, st)

  #class DFA
  t = dict()
  t[(0, 'class')] = 1
  t[(1, ' ')] = 2
  t[(2, word)] = 3
  t[(3, ' ')] = 5
  t[(4, ' ')] = 5
  t[(5, '{')] = 8
  t[(6, ' ')] = 7
  t[(7, '{')] = 8
  st = dict()
  st[(3, '[')] = (typeParamDFA, 3)
  st[(3, '(')] = (paramListDFA, 4)
  st[(5, 'extends')] = (extendsDFA, 6)

  classDFA = DFA("class", t, 0, {4, 8}, st)


def parseDef(ctx):
  return DFAs.defDFA.run(ctx)

def parseClass(ctx):
  return DFAs.classDFA.run(ctx)

def formatLine(line1):
   return "\t" + bcolors.OKBLUE + str(line1.lineNumber) + bcolors.ENDC + "\t" + line1.contents

def formatTwoLines(line1, line2):
  return "\t" + bcolors.OKBLUE +  str(line1.lineNumber) + bcolors.ENDC  + "\t" + line1.contents + "\n\t" + bcolors.OKBLUE + str(line2.lineNumber) + bcolors.ENDC + "\t" + line2.contents


def getAndClipLinesStartingWith(lines, prefix):
  return [elem.trimPrefix(prefix) for elem in lines if elem.startswith(prefix)]


def readDirectories():
  try:
    contents = open("formatCheckerDirectories.txt").read()
    return contents.split(",")
  except: IOError
  return []

def writeDirectories(directories):
   file = open("formatCheckerDirectories.txt", 'w')
   file.write(directories)
   file.close()


class FileOps:
  @staticmethod
  def getAllFiles(directories):
    currentDirectory = check_output(["pwd"]).strip()
    files = []
    for directory in directories:
      print directory
      os.chdir(directory)
      output = check_output(["ls", "-R"])
      lines = output.split("\n")
      parent = ""

      for line in lines:
        line = line.lstrip()
        if line.endswith(":"):
          parent = line[len("./"):]
          parent = parent[:-1]
        elif line.endswith(".scala") and not parent.startswith("."):
          files.append(directory + "/" + parent + "/" + line)
          fileName = directory + "/" + parent + "/" + line
          _file = File(fileName)
    os.chdir(currentDirectory)
    return files

  @staticmethod
  def getModifiedFiles(directories):
    currentDirectory = check_output(["pwd"]).strip()
    files = []
    for directory in directories:
      print directory
      os.chdir(directory)
      gitOutput = check_output(["git", "status"])
      lines = gitOutput.split("\n")
      for line in lines:
        if line.endswith(".scala"):
          files.append(line[len('\t'):])
    os.chdir(currentDirectory)
    return files

def main():
  directories = readDirectories()
  print directories
  if "init" in sys.argv or not directories:
    print "Let's set up your Scala style checker.\n" \
          "Enter the absolute paths of the directories to check, separated by commas."
    directories = raw_input()
    writeDirectories(directories)
    directories = directories.split(",")
    print "Successfully initialized. Created file 'formatCheckerDirectories.txt'"

  if "check-all" in sys.argv:
    print "Style-checking all files in directories:"
    fileNames = FileOps.getAllFiles(directories)
  else:
    print "Style-checking modified files in directories."
    fileNames = FileOps.getModifiedFiles(directories)

  searchedFiles = 0
  for fileName in fileNames:
    #print fileName
    file = File(fileName)
    file.checkFormatting()
    searchedFiles +=1
    if file.hasIssue:
      file.printIssues()
      Results.issueFiles+=1

  if searchedFiles == 1:
    print "Searched " + str(searchedFiles) + " file for style."
  else:
    print "Searched " + str(searchedFiles) + " files for style."

  if Results.issueCount == 0:
    print bcolors.OKGREEN + "Looks good!" + bcolors.ENDC
  elif Results.issueCount == 1:
    print bcolors.WARNING + "Found " + str(Results.issueCount) + " issue in " + str(Results.issueFiles) + " files." + bcolors.ENDC
  else:
    print bcolors.WARNING + "Found " + str(Results.issueCount) + " issues in " + str(Results.issueFiles) + " files." + bcolors.ENDC

main()


