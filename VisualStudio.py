#----------------------------------------------------------------------
# Copyright (c) 2013, Guy Carver
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#
#     * The name of Guy Carver may not be used to endorse or promote products # derived#
#       from # this software without specific prior written permission.#
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# FILE    VisualStudio.py
# BY      Guy Carver
# DATE    06/05/2013 09:06 PM
#----------------------------------------------------------------------

import sublime, sublime_plugin
import functools
import re
import os, sys

dte_settings = None
packagepath = os.path.dirname(__file__)

sys.path.append(packagepath)

import dte

#--------------------------------------------------------
def plugin_loaded(  ) :
  global dte_settings
  dte_settings = sublime.load_settings("VisualStudio.sublime-settings")
  v = dte_settings.get("version", "16.0")
  objectName = "VisualStudio.DTE." + v
  dte.open(objectName)

#--------------------------------------------------------
def GetAllBreakpoints(  ):
  ''' Get array of all breakpoints with (filename, linenum) tuple. '''
  bps, cnt = dte.breakpoints()
  breaks = [dte.breakpoint(bps, i) for i in range(cnt)]
  return breaks

#--------------------------------------------------------
def GetBreakpoints( aView, aOn ) :
  ''' Get array of breakpoints with (index, linenum) tuple. '''
  bps, cnt = dte.breakpoints()
  breaks = []
  fname = format(aView.file_name()).lower()
  for i in range(cnt):
    data = dte.breakpoint(bps, i)
    if (data.File != None) and (data.Enabled == aOn):
      if fname == data.File.lower():
        breaks.append(data)
  return breaks

#--------------------------------------------------------
def ShowBreakpoints( aView, aList, aType, aColor ) :
  aView.erase_regions(aType)
  if aList :
    g = lambda line: aView.line(aView.text_point(line - 1, 0))
    regs = [ g(brk.Line) for brk in aList ]
    aView.add_regions(aType, regs, aColor, "dot", sublime.HIDDEN)

#--------------------------------------------------------
def UpdateBreakpoints( aView ) :
  if aView.file_name() and dte_settings.get("showbreakpoints") :
    onA = GetBreakpoints(aView, True)
    oncolor = dte_settings.get("bpointoncolor", "red")
#    print("On: " + str(len(bon)))
    ShowBreakpoints(aView, onA, "breakon", oncolor)
    offA = GetBreakpoints(aView, False)
    offcolor = dte_settings.get("bpointoffcolor", "gray")
    ShowBreakpoints(aView, offA, "breakoff", offcolor)

#--------------------------------------------------------
def SetFileAndLine( aView ) :
  sel = aView.sel()[0]
  line, _ = aView.rowcol(sel.begin())
  fl = aView.file_name()
#  print('filename', fl)
  res = dte.setfile(fl, line + 1)
  return res

#--------------------------------------------------------
class DteSelectBreakpointCommand( sublime_plugin.WindowCommand ) :
  def run( self ) :
    brks = GetAllBreakpoints()
    brkdata = [ b.File + ":" + str(b.Line) for b in brks ]
    self.window.show_quick_panel(brkdata, functools.partial(self.on_done, brkdata))

  #--------------------------------------------------------
  def on_done( self, aBreaks, aIndex ) :
    if aIndex != -1 :
      path = aBreaks[aIndex]
      vw = self.window.open_file(path, sublime.ENCODED_POSITION)

#--------------------------------------------------------
class DteToggleBreakpointCommand( sublime_plugin.TextCommand ) :
  #--------------------------------------------------------
  def run( self, edit ) :
    # print("Setting file and line.")
    res = SetFileAndLine(self.view)
    if res:
#      print("ToggleBreakPoint")
      dte.command("Debug.ToggleBreakPoint", "")
      # print("UpdatingBreakPoint")
      UpdateBreakpoints(self.view)

#--------------------------------------------------------
class DteEnableBreakpointCommand( sublime_plugin.TextCommand ) :

  #--------------------------------------------------------
  def run( self, edit ) :
    # print("Setting file and line.")
    res = SetFileAndLine(self.view)
    if res:
      # print("ToggleBreakPoint")
      dte.command("Debug.EnableBreakPoint", "")
      # print("UpdatingBreakPoint")
      UpdateBreakpoints(self.view)

#--------------------------------------------------------
class DteSetFileLineCommand( sublime_plugin.TextCommand ) :

  #--------------------------------------------------------
  def run( self, edit ) :
    # print("Setting fileandline")
    SetFileAndLine(self.view)

compileFileName = re.compile("^.*Compile:[ \t]+([\w.]*).*", re.MULTILINE | re.IGNORECASE)

#--------------------------------------------------------
#If on a secondary file attempt to find the main .cpp file to compile.  Either change filename extension to
# .cpp or find the filename in the Compile: field of the file header.
class DteCompilecppCommand( sublime_plugin.WindowCommand ) :
  #--------------------------------------------------------
  def run( self ) :
    vw = self.window.active_view()
    if not vw.is_scratch() :
      if vw.is_dirty():
        vw.run_command("save")

      fname = self.FindCompileFileName(vw)
      if not fname :
        fname = vw.file_name()
      #Get file name and make sure extension is .cpp.
      if fname :
        fpath, fext = os.path.splitext(fname)
        fname = fpath + '.cpp'
#        print("opening " + fname)
        res = dte.command("File.OpenFile", fname)
        if res:
          dte.command("Build.Compile", "")
        else:
          print("Failed to compile " + fname)

  #--------------------------------------------------------
  #Look for Compile: in the header and use the filename indicated by that to compile instead of current file.
  def FindCompileFileName( self, vw ) :
    #This may be temporary.  Need to use a comment range perhaps?
    name = None
    hr = vw.extract_scope(4)  #We start at offset 4 to skip the // and get to the comment body, otherwise our range in only (0,2) for // and (0,3) for ///
    lt = vw.substr(hr)
#    print("testing " + lt)
    match = compileFileName.search(lt)
    if (match != None) :
      name = match.group(1)
      print("Compile: " + name)

    return name

#--------------------------------------------------------
class DteCommandCommand( sublime_plugin.TextCommand ) :
  #--------------------------------------------------------
  def run( self, edit, command, syncfile = True, save = False ) :
    if save and self.view.is_dirty():
      self.view.run_command("save")

    if syncfile :
      SetFileAndLine(self.view)

    res = dte.command(command, "")

#--------------------------------------------------------
#def SyncFileLine( aDTE, aWindow ) :
#  doc = aDTE.ActiveDocument
#  if doc :
#    textDoc = doc.Object("TextDocument")
#    sel = textDoc.Selection
#    tp = sel.TopPoint
#    line = tp.Line
#    path = doc.FullName + ":" + str(line)
#    vw = aWindow.open_file(path, sublime.ENCODED_POSITION)
#    # This doesn't currently work.
#    # if vw:
#    #   while (vw.is_loading()) :
#    #     pass
#    #   UpdateBreakpoints(vw)

#--------------------------------------------------------
#class DteSyncFileLineCommand( sublime_plugin.WindowCommand ) :
#  #--------------------------------------------------------
#  def run( self ) :
#    with MyDTE(lambda x : sublime.status_message("SyncFileLine failed")) as dte :
#      SyncFileLine(dte, self.window)

#--------------------------------------------------------
class DteBreakUpdater(sublime_plugin.EventListener):
  #--------------------------------------------------------
  def on_activated( self, view ) :
    UpdateBreakpoints(view)


