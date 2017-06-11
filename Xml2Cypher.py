#!/usr/bin/env python

#
# Last modification: 2017-06-10
# Homepage: 
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# ITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

# Regular expressions
import re
# Containers copy/deepcopy
import copy
# System - used for exception augmentation
import sys
# Collections
import collections
# Enums
from enum import Enum
# Ordered dictionaries (xmltodict)
from collections import OrderedDict

# CQL
import CypherWriter
# Id generator
import IdHelper


#
#
# Utils
ids = IdHelper.IdHelper()
  
#
# Select error type to be thrown based on several rules
def getError(o, expectedType, defaultError, validation = True):
  if not o:
    return ValueError
  
  elif expectedType and not isinstance(o, expectedType):
    return TypeError
  
  if defaultError and not validation:
    return defaultError
  
  return None

def raiseError(o, ctxt, errorType, token, msg):
  raise errorType(
    "{}, while matching '{}'.\nVariables: {}\nTypes: {}\nGot object: {}".format(
      msg, token, ctxt.variables, ctxt.types, o
    )
  )

#
# Check whether o is a primitive type
def isPrimitive(o):
  return type(o) in { str, int, float, bool }

#
# Check whether o is of collection type
def isCollection(o):
  return                                            \
    isinstance(o, collections.abc.Collection) and   \
    not isinstance(o, str)

def idem(o):
  return o

def safeInt(s):
  try:
    return int(s)
  except ValueError:
    return None

def safeFloat(s):
  try:
    return float(s)
  except ValueError:
    return None

def safeBool(s):
  return { 'True': True, 'False': False }.get(s, None)

def unsafeBool(s):
  ret = safeBool(s)
  
  if not ret:
    raise ValueError('Not a boolean: ' + s)
  
  return ret

def strToVal(s):
  if not s:
    return None
    
  if len(s) > 1 and s[0] == s[-1] == '"':
    return s[1:-1]
  
  return safeInt(s) or safeFloat(s) or safeBool(s)

def extractVar(s, ctxt, o, default = None, shouldRaise = True):
  # Replace variables if necessary
  m = RE_Variable.match(s)
  var = default
  
  if m:
    var = ctxt.getVar(m.group(2))
    
    if not var:
      if shouldRaise:
        raiseError(o, ctxt, SyntaxError, s, "No such variable")
      
      return None
    
  return var

def expandVar(s, ctxt, o, shouldRaise = True):
  # Replace variables if necessary
  m = RE_Variable.match(s)
  
  while m:
    var = ctxt.getVar(m.group(2))
    
    if not var:
      if shouldRaise:
        raiseError(o, ctxt, SyntaxError, s, "No such variable")
      
      return None
    
    s = m.group(1) + str(var) + m.group(3)
    m = RE_Variable.match(s)
    
  return s

#
# Parse property list {properties} into {schemaProperties}
def parseProperties(properties, parentName, ctxt):
  schemaProperties = []
  
  # Parse properties
  m = RE_Property_Split.match(properties)
  
  while m:
    # m[:-1] => Ignore CONST_RE_Property_List which gives us a 6-uple
    schemaProperties.append(SchemaProperty(m, parentName, ctxt))
    # CONST_RE_Property_List which was omitted ^
    properties = m.group(6)
    
    m = RE_Property_Split.match(properties)
  
  # No more split -- either there were no parameter to begin with, or this
  # is the last one
  m = RE_Property.match(properties)
  if m:
    schemaProperties.append(SchemaProperty(m, parentName, ctxt))
  
  return schemaProperties

#
# Fixes xmlToDict inconsistent behavior with dictionaries
def normalizeDict(object):
  if not isinstance(object, list):
    return [ object ]
  
  return object

#
#
# Enums
DefinitionModes = Enum('DefinitionMode', 'type struct schema')
PrimitiveTypes = Enum('PrimitiveType', 'string int float boolean id idem')


#
#
# Constants
CONST_Token_Types = "types:"
CONST_Token_Structures = "structures:"
CONST_Token_Schema = "schema:"

CONST_RE_Ws = r'\s*'
CONST_RE_PWs = r'(\s*)'
CONST_RE_Optional = r'(\?)?'
CONST_RE_OptCond = r'(\?|!)?'
CONST_RE_Variable = r'(.*)\$\{(\w+)\}(.*)'
CONST_RE_Comment = r'\s*(#.*)?'
CONST_RE_Index = r'\[(\d+)\](\*)?'
CONST_RE_Literal = '".*"'
# Note: @CREATE is assumed by default, but has been added for consistency
CONST_RE_Options = '(@MERGE|@CREATE|@ADDMOREOPTIONS)*'
# Matches identifiers, e.g. Person, Authenticated${Role}, string, ...
CONST_RE_Id_Req = CONST_RE_Ws + r'(\w+|\$\{\w+\})' + CONST_RE_Ws
CONST_RE_Id_Opt = CONST_RE_Ws + r'(\w+|\$\{\w+\})?' + CONST_RE_Ws
CONST_RE_LitId_Opt = CONST_RE_Ws + r'(\w+|\$\{\w+\}|".*")?' + CONST_RE_Ws

# Matches all characters in a path, used as a "macro"-regexp. Actual tokens are extracted using Token or Token_Split
# e.g. 'Descriptions:[0]:@summary'
CONST_RE_Path = r'((?:[\[\]\*$\{\}@\w\s\:]*|\s*".*"\s*|\s*#\{.*?\}\s*)(?:\:(?:[\[\]\*$\{\}@\w\s\:]*|\s*".*"\s*|\s*#\{.*?\}\s*))*)?'
# Matches a token inside a path, that is, one of the following:
# element, "literal", @attribute, [index], [index]*, #{funcName, params}
CONST_RE_Token = r'\s*(\[\d+\]\*?|"[^"]*"|@\w+|\w+|#\{.*\})\s*'
# Matches {token}:{path}, in other words, extracts a token out of a path
CONST_RE_Token_Split = CONST_RE_Token + ':' + CONST_RE_Path
# Matches '{optional?}{identifier}:{path}->{return_type} as {alias}, (repeat)'
CONST_RE_Property_List = '(.*?)' #'((?:' + CONST_RE_Property + '(?:,' + CONST_RE_Property + ' #r'([\[\]\*\?!"$\{\}@\w\s:\->,]*)'
# Matches '{optional,conditional?}{identifier}:{path}->{return_type} as {alias}'
CONST_RE_Property =                                       \
  CONST_RE_Ws + CONST_RE_OptCond + CONST_RE_LitId_Opt +   \
  ':' + CONST_RE_Path + '->' + CONST_RE_Id_Req +          \
  '(?:as ' + CONST_RE_Id_Req + ')?' + CONST_RE_Ws
#r'\s*(\?|!)?\s*([\w\s"\-]*)\s*:' + CONST_RE_Path + '->\s*(\w+)\s*(as\s+(\w+))?\s*'
# Matches {parameter}:{property_list}, in other words, extract a parameter out of a parameter list
CONST_RE_Property_Split = CONST_RE_Property + ',' + CONST_RE_Property_List
# Matches #{{function_name},{property_list}}
CONST_RE_Function = '#\{' + CONST_RE_Id_Req + '(?:,' + CONST_RE_Property_List + ')?\}'

# Identation does not matter. Identifier, path and return type mandatory.
# Matches {typename}:{path}->{return_type}
CONST_RE_Type = CONST_RE_Id_Req + ':' + CONST_RE_Path + '->' + CONST_RE_Id_Req
# Mandatory indentation. Optional 'optional' and label. Mandatory tag. Optional parameters, collection, and options
# Matches {whitespace}{optional?}{label}:{tag}({property_list}){collection?[]}->{return_type}({return_type_Property_list}){@option1@option2...}
CONST_RE_Node =                                                         \
  CONST_RE_PWs + CONST_RE_Optional +                                    \
  CONST_RE_Id_Opt + ':' + CONST_RE_Id_Opt +                             \
  '\(' + CONST_RE_Property_List + '\)' + CONST_RE_Ws +                  \
  '(\[\])?' + CONST_RE_Ws +                                             \
  '(->' + CONST_RE_Id_Req + '\(' + CONST_RE_Property_List + '\))?' +  \
  CONST_RE_Options
# Matches {whitespace}{src_node}({src_node_props})-[{rs_name}({rs_params})]->{target_node}({target_node_props})
CONST_RE_Relationship =                                                                         \
  CONST_RE_PWs + CONST_RE_Optional +                                                            \
  CONST_RE_Id_Req + '\(' + CONST_RE_Property_List + '\)' + CONST_RE_Ws +                        \
  '-\[' + CONST_RE_Id_Req + '\(' + CONST_RE_Property_List + '\)' + CONST_RE_Ws + '\]' + '->' +  \
  CONST_RE_Id_Req + '\(' + CONST_RE_Property_List + '\)'
#r'(\s*)([\w$]+)\(' + CONST_RE_Property_List + '\)-\[\s*([\w$]+)\(' + CONST_RE_Property_List + '\)\s*\]->([\w$]+)\(' + CONST_RE_Property_List + '\)'

CONST_Primitives = \
{
  PrimitiveTypes.string.name: str,
  PrimitiveTypes.int.name: int,
  PrimitiveTypes.float.name: float,
  PrimitiveTypes.boolean.name: unsafeBool,
  PrimitiveTypes.id.name: int,
  PrimitiveTypes.idem.name: idem
}


#
#
# Regular expressions
def compile(pattern):
  return re.compile('^' + pattern + '$')

RE_Variable = compile(CONST_RE_Variable)
RE_Comment = compile(CONST_RE_Comment)
RE_Index = compile(CONST_RE_Index)

RE_Path = compile(CONST_RE_Path)
RE_Token = compile(CONST_RE_Token)
RE_Token_Split = compile(CONST_RE_Token_Split)
RE_Property_Split = compile(CONST_RE_Property_Split)
RE_Property = compile(CONST_RE_Property)
RE_Function = compile(CONST_RE_Function)

RE_Type = compile(CONST_RE_Type)
RE_Node = compile(CONST_RE_Node)
RE_Relationship = compile(CONST_RE_Relationship)

#
#
# Core

# Holds scope-specific context data
class Context:
  
  def __init__(self, vars, types, functions, nodeWriter, rsWriter, uncheckedTypes):
    # Variables, either automatic or schema-defined
    self.variables = vars
    # Loaded types, should remain the same in every scope
    self.types = types
    # User-defined functions
    self.functions = functions
    
    # Writers
    self.nodeWriter = nodeWriter
    self.rsWriter = rsWriter
    
    self.uncheckedTypes = uncheckedTypes
  
  def isUnchecked(self):
    return self.uncheckedTypes
  
  #
  # Self-explanatory
  def getVar(self, key):
    return self.variables[key] if key in self.variables else None
  
  def getType(self, key):
    return self.types[key][0] if key in self.types else CONST_Primitives.get(key, None)
  
  #
  # Self-explanatory
  def addType(self, key, t):
    l = self.types[key] if key in self.types else None
    
    self.types[key] = l + [ t ] if l else [ t ]
  
  #
  # Self-explanatory
  def addVariable(self, key, o):
    self.variables[key] = o
  
  def applyFunction(self, funcName, params):
    ret = None
    
    if funcName in self.functions:
      ret = self.functions[funcName](params)
    
    return ret
  
  #
  # Convert {o} using pre-defined type: either structure or type
  def convert(self, o, targetType):
    l = self.types.get(targetType, None)
    count = 0
    if l:
      for t in l:
        count += 1
        ret = t.apply(o, self)
      
      return ret
    
    f = CONST_Primitives.get(targetType, None)
    return f(o) if f else None
  
  def newContext(self):
    return Context(
      copy.copy(self.variables),
      self.types,
      self.functions,
      self.nodeWriter,
      self.rsWriter,
      self.isUnchecked
    )

class SchemaBaseValue:
  path = None
  
  #
  # Generate and throw error. See {getError}
  """
  def _raiseError(self, o, expectedType, defaultError, token, msg, validation = True):
    self.raiseError(
      o,
      getError(o, expectedType, defaultError, validation),
      token,
      msg
    )
  """
  
  #
  # Generate and throw error. See {getError}
  def raiseError(self, o, errorType, token, ctxt, msg):
    raise errorType(
      "{}, while matching '{}' in path '{}'.\nVariables: {}\nTypes: {}\nGot object: {}".format(
        msg, token, self.path, ctxt.variables, ctxt.types, o
      )
    )
  
  #
  # Traverse {count} chained arrays, along index {idx}.
  def traverseArrays(self, o, idx, count = 999):
    while isinstance(o, list) and len(o) > idx and count > 0:
      o = o[idx]
      count -= 1
    
    if count > 0 or not o:
      return ( None, getError(o, list, IndexError) )
    
    return ( o, None )
  
  #
  #
  def traversePath(self, path, o, ctxt):
    token = None
    
    # Replace variable if necessary
    path = expandVar(path, ctxt, o)
    
    # Attempt to split current token from path
    m = RE_Token_Split.match(path)
    if m:
      token = m.group(1)
      path = m.group(2)
    
    # Attempt to extract terminal element ; If non-terminal, assume _ as path
    else:
      m = RE_Token.match(path)
      if not m:
        self.raiseError(o, SyntaxError, path, ctxt, "Invalid path")
      
      token = m.group(1)
      path = '_'
    
    # Terminal element: text
    if token == '_':
      if o and '#text' in o:
        o = o['#text']
        
      err = getError(o, None, ValueError, ctxt.isUnchecked or isPrimitive(o))
      return                                                            \
        o if not err                                                    \
        else self.raiseError(o, err, token, ctxt, "Unexpected object")
    
    # Terminal element: attribute
    if token[0] == '@':
      err = getError(o, OrderedDict, KeyError, token in o)
      return                                                            \
        o[token] if not err                                             \
        else self.raiseError(o, err, token, ctxt, "Unexpected object")
    
    # Terminal element: primitive type
    v = strToVal(token)
    if v != None:
      return v
    
    # Is it a function ?
    m = RE_Function.match(token)
    if m:
      funcName, propsStr = m.groups()
      scopedCtxt = ctxt.newContext()
      props = {}
      
      for prop in parseProperties(propsStr, None, scopedCtxt):
        ret = prop.apply(o, scopedCtxt)
        
        if not ret[1]:
          return None
        
        if prop.typename:
          props[prop.typename] = ret[0]
      
      o = scopedCtxt.applyFunction(funcName, props)
      return self.traversePath(path, o, ctxt)
    
    # Is it an index ?
    m = RE_Index.match(token)
    if m:
      idx, recursive = m.groups()
      idx = int(idx)
      
      o, err =                                      \
        self.traverseArrays(o, idx) if recursive    \
        else self.traverseArrays(o, idex, 1)
      
      if err:
        self.raiseError(o, err, token, ctxt, "Unexpected object")
      
      return self.traversePath(path, o, ctxt)
    
    # An element ?
    if isinstance(o, OrderedDict) and token in o:
      return self.traversePath(path, o[token], ctxt)
    
    # Unknown error
    self.raiseError(o, ValueError, token, ctxt, "Unexpected object")
  
  #
  # Apply defined schema to node object
  def apply(self, o, ctxt):
    return self.traversePath(self.path, o, ctxt)

class SchemaType(SchemaBaseValue):
  
  def __init__(self, typename, path, typeret, ctxt):
    self.typename = typename
    self.path = path
    self.typeret = typeret
    
    if ctxt:
      ctxt.addType(self.typename, self)
  
  # Recursively check for final type (accounting for chained types)
  def getRealType(self, ctxt):
    type = ctxt.getType(self.typeret)
    
    if isinstance(type, SchemaType):
      return type.getRealType(ctxt)
    
    return self.typeret
  
  #
  # Apply defined schema to node object
  def apply(self, o, ctxt):
    return ctxt.convert(super().apply(o, ctxt), self.typeret)

# Properties are types with an alias and an optional identifier (typename)
class SchemaProperty(SchemaType):
  
  def __init__(self, match, parentName, ctxt):
    self.isOptional = False
    self.isConditional = False
    self.alias = None
    self.matchValue = None
    self.parentName = parentName
    
    super().__init__(match.group(2), match.group(3), match.group(4), None)
    
    # Optional, Conditional ?
    if match.group(1):
      if match.group(1) == '!':
        self.isConditional = True
      
      elif match.group(1) == '?':
        self.isOptional = True
    
    # Specified alias
    if match.group(5):
      self.alias = match.group(5)
    
    # Is typename a value ?
    self.matchValue = strToVal(self.typename)
    
    if self.matchValue:
      self.typename = None
    
    # id types have a default alias name
    elif not self.alias and self.getRealType(ctxt) == PrimitiveTypes.id.name and parentName:
      self.alias = parentName + 'Id'
  
  #
  # Apply defined schema to node object
  def apply(self, o, ctxt):
    try:
      # Apply path
      if any(self.path):
        ret = ( super().apply(o, ctxt), True )
      
      # Auto-generate ID
      elif self.parentName:
        ret = ( ids.new(self.parentName), True )
      
      # Error in schema
      else:
        raiseError(o, ctxt, ValueError, self.path, 'Empty path')
      
      # A value was provided as {typename} - check ret against it
      if self.matchValue:
        if self.matchValue == ret[0]:
          return ( None, True )
        else:
          raiseError(ret[0], ctxt, ValueError, self.path, 'Unmatched value: "%s"' % self.matchValue)
      
      # Add alias to context variables
      if self.alias:
        ctxt.addVariable(self.alias, ret[0])
      
      return ret
    except BaseException as e:
      if self.isOptional:
        return ( None, True )
      
      elif self.isConditional:
        return ( None, False )
      
      raise e

#
#
class SchemaRelationship:
  
  def __init__(self, match, ctxt):
    self.indent = -1
    self.optional = False
    self.srcNode = None
    self.srcNodeId = None
    self.tgtNode = None
    self.tgtNodeId = None
    self.rsName = None
    
    self.srcNodeProps = []
    self.tgtNodeProps = []
    self.rsProperties = []
    
    self.schema = match.group(0).lstrip()
  
    indent, isOptional, self.srcNode, self.srcNodePropsStr, self.rsName,   \
      self.rsPropsStr, self.tgtNode, self.tgtNodePropsStr = match.groups()
    
    self.indent = len(indent)
    self.isOptional = isOptional != None
    self.rsProperties = parseProperties(self.rsPropsStr, None, ctxt)
    self.srcNodeProps = parseProperties(self.srcNodePropsStr, None, ctxt)
    self.tgtNodeProps = parseProperties(self.tgtNodePropsStr, None, ctxt)

  def __str__(self):
    return self.schema

  def mapProps(self, o, props, ctxt):
    propMap = {}
    
    for prop in props:
      ret = prop.apply(o, ctxt)
      
      if ret[0] and ret[1] and prop.typename:
        propMap[prop.typename] = ret[0]
    
    return propMap
  
  def apply(self, o, ctxt):
    try:
      srcNodePropMap = self.mapProps(o, self.srcNodeProps, ctxt)
      tgtNodePropMap = self.mapProps(o, self.tgtNodeProps, ctxt)
      rsPropMap = self.mapProps(o, self.rsProperties, ctxt)
      
      ctxt.rsWriter.relationship(
        expandVar(self.srcNode, ctxt, o),
        srcNodePropMap,
        expandVar(self.tgtNode, ctxt, o),
        tgtNodePropMap,
        expandVar(self.rsName, ctxt, o),
        rsPropMap
      )
      
      return True
      
    except BaseException as e:
      if not self.isOptional:
        # Add line number and content to exception message
        parent = o.keys() if isinstance(o, OrderedDict) else o
        e =                                                                   \
          type(e)(    
            str(e) +                                                          \
            "\n\nWhile parsing item '" +                                      \
            str(self) +                                                       \
            "' in parent:\n" + str(parent)                                    \
          )                                                                   \
          .with_traceback(sys.exc_info()[2])
        
        # Re-raise augmented exception
        raise e from None

    return False
#
# 
class SchemaNode:
  
  def __init__(self, match, ctxt):
    self.indent = -1
    self.isOptional = False
    self.isCollection = False
    self.isMerge = False
    self.label = None
    self.returnType = None
    self.tag = None
    
    self.alwaysRaise = False
    
    self.children = []
    self.properties = []
    self.returnTypeProperties = []
    
    self.schema = match.group(0).lstrip()
    
    indent, isOptional, self.label, self.tag, properties,   \
      isCollection, i,self.returnType, returnTypeProperties,  \
      options = match.groups()
    
    self.indent = len(indent)
    self.isOptional = isOptional != None
    self.isCollection = isCollection != None
    
    if options:
      self.isMerge = '@MERGE' in options
    
    # Parse properties
    self.properties = parseProperties(properties, self.label, ctxt)
    
    # Optional return type
    if returnTypeProperties:
      self.returnTypeProperties = parseProperties(returnTypeProperties, None, ctxt)
  
  def __str__(self):
    return self.schema
  
  #
  # Self-explanatory
  def addChildNode(self, child):
    self.children.append(child)
  
  def apply_element(self, node, ctxt):
    self.alwaysRaise = False
    
    propMap = {}
    restoreCtxt = ctxt.newContext()
  
    for prop in self.properties:
      ret = prop.apply(node, ctxt)
      
      if ret[0] and ret[1] and prop.typename:
        propMap[prop.typename] = ret[0]
      
      elif not ret[1]:
        ctxt.variables = restoreCtxt.variables
        return False
    
    if self.returnType:
      scopedCtxt = ctxt.newContext()
      
      for returnTypeProp in self.returnTypeProperties:
        returnTypeProp.apply(node, scopedCtxt)
        
      if scopedCtxt.convert(node, self.returnType) == None:
        raiseError(node, ctxt, ValueError, '->' + self.returnType, 'No such type: ' + self.returnType)
      
    elif self.label:
      ctxt.nodeWriter.node(self.label, propMap, self.isMerge)
    
    self.alwaysRaise = True
    
    scopedCtxt = ctxt.newContext()
    for child in self.children:
      child.apply(node, scopedCtxt)
    
    return True

  #
  # Apply defined schema to node object
  def apply(self, o, ctxt):
    try:
      self.alwaysRaise = False
      
      if self.returnType or not self.tag:
        return self.apply_element(o, ctxt)
      
      else:
        node = extractVar(self.tag, ctxt, o)
      
        if not self.isCollection:
          if not node:
            node = o[expandVar(self.tag, ctxt, o)]
          
          return self.apply_element(node, ctxt)
        
        else:
          scopedCtxt = ctxt.newContext()
          
          if not node:
            node = o[expandVar(self.tag, scopedCtxt, o)]
          
          for childNode in normalizeDict(node):
            ret = self.apply_element(childNode, scopedCtxt)

      return ret
    except BaseException as e:
      if self.alwaysRaise:
        raise e
        
      if not self.isOptional:
        # Add line number and content to exception message
        parent = o.keys() if isinstance(o, OrderedDict) else o
        e =                                                                   \
          type(e)(    
            str(e) +                                                          \
            "\n\nWhile parsing item '" +                                      \
            str(self) +                                                       \
            "' in parent:\n" + str(parent)                                    \
          )                                                                   \
          .with_traceback(sys.exc_info()[2])
        
        # Re-raise augmented exception
        raise e from None
      
    return False

#
#
class SchemaRoot:
  children = None
  
  def __init__(self, children):
    self.children = children

  def apply(self, o, ctxt):
    scopedCtxt = ctxt.newContext()
    
    for child in self.children:
      child.apply(o, scopedCtxt)

#
#
class X2CSchema:
  
  def __init__(self, root, ctxt):
    self.root = root
    self.context = ctxt

  #
  # Apply defined schema to node object
  def apply(self, o, nodeWriter, rsWriter, userFunctions = None, uncheckedTypes = False):
    if userFunctions != None:
      self.context.functions = userFunctions
    
    self.context.nodeWriter = nodeWriter
    self.context.rsWriter = rsWriter
    
    self.context.uncheckedTypes = uncheckedTypes
    
    self.root.apply(o, self.context)

#
#
class SchemaParser:
  
  def __init__(self):
    self.lineCount = 1
    self.mode = DefinitionModes.schema
    self.modeParseFunc = self.parseStructOrSchema
    
    self.context = Context({}, {}, {}, None, None, False)
    self.nodeStack = []
    self.rootStack = []
  
  #
  #
  # Definitions modes
  
  def parseTypeToken(self, line):
    self.mode = DefinitionModes.type
    self.modeParseFunc = self.parseType
  
  def parseStructureToken(self, line):
    self.mode = DefinitionModes.struct
    self.modeParseFunc = self.parseStructOrSchema
    self.nodeStack = []
    
  def parseSchemaToken(self, line):
    self.mode = DefinitionModes.schema
    self.modeParseFunc = self.parseStructOrSchema
    self.nodeStack = []
  
  #
  #
  # Core
  
  def autoMatch(self, line):
    m = RE_Node.match(line)
    if m:
      return SchemaNode(m, self.context)
    
    m = RE_Relationship.match(line)
    if m:
      return SchemaRelationship(m, self.context)
    
    return None
  
  def parseType(self, line):
    m = RE_Type.match(line)
    
    if m:
      s = SchemaType(m.group(1), m.group(2), m.group(3), self.context)
      
    else:
      raise SyntaxError('Unrecognized syntax')
  
  def parseStructOrSchema(self, line):
    parent = None
    n = self.autoMatch(line)
    
    if n:
      # Unstack until we match a parent, or no parent node is left
      while len(self.nodeStack) > 0:
        parent = self.nodeStack.pop()
        
        if n.indent > parent.indent:
          break
        
        parent = None
      
      # This is a deeper node or relationship
      if parent:
        parent.addChildNode(n)
        self.nodeStack.append(parent)
        
        # For usage with eventual children
        if isinstance(n, SchemaNode):
          self.nodeStack.append(n)
      
      # This is a structure's root, but we've got a relationship
      elif isinstance(n, SchemaRelationship):
        raise SyntaxError('Expected a node, but got a relationship')
      
      # This is a structure's root
      else:
        self.nodeStack = [n]
        
        if self.mode == DefinitionModes.struct:
          self.context.addType(n.tag, n)
        
        else:
          self.rootStack.append(n)
      
    else:
      raise SyntaxError('Unrecognized syntax')
  
  def isComment(self, line):
    return RE_Comment.match(line)
  
  def parseDefault(self, line):
    try:
      if self.isComment(line):
        return None
      
      self.modeParseFunc(line)
      # throw ?
      
    except BaseException as e:
      # Add line number and content to exception message
      e =                                                                   \
        type(e)(    
          str(e) +                                                          \
          "\n\nWhile parsing line " +                                       \
          str(self.lineCount) +                                             \
          ":\n\"" + line + "\""                                             \
        )                                                                   \
        .with_traceback(sys.exc_info()[2])
      
      # Re-raise augmented exception
      raise e from None
  
  def matchLine(self, line):
    {
      CONST_Token_Types: self.parseTypeToken,
      CONST_Token_Structures: self.parseStructureToken,
      CONST_Token_Schema: self.parseSchemaToken
    }.get(line, self.parseDefault)(line)
    
    self.lineCount += 1

def parse(schema):
  sp = SchemaParser()
  
  with open(schema, 'r') as fp:
    for line in fp:
      sp.matchLine(line.rstrip('\r\n\t '))
  
  # Create root node
  root = SchemaRoot(sp.rootStack)
  
  return X2CSchema(root, sp.context)
