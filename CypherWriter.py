#!/usr/bin/env python

# For hash identification
import hashlib
# OrderedDict
from collections import OrderedDict

# When enabled, strips unnecessary whitespaces
CONST_Optimize = False


#
# Helper class, define methods used in writing Cypher commands to file.
class CypherWriter:
  
  def __init__(self, filename):
    self.cmdCounter = 0
    self.rsDict = {}
    self.rsProps = {}
  
    self.file = open(filename, "w+", encoding="utf8")
  
  #
  # Write {buff} to file
  def write(self, buff):
    # Legacy - This will wreck text properties values
    if False and CONST_Optimize is True:
      buff = buff.replace('  ', '')
      buff = buff.replace(', ', ',')
      buff = buff.replace(': ', ':')
      buff = buff.replace(' (', '(')
      #buff = buff.strip('\t\n')
    
    self.file.write(buff)
  
  def sanitize(self, buff):
    buff = buff.replace('\\', '\\\\')
    buff = buff.replace('\r\n', '\\r\\n')
    buff = buff.replace('\n', '\\n')
    buff = buff.replace('\r', '\\r')
    buff = buff.replace('"', '\\"')
    
    return buff
  
  #
  # Legacy comment:
  # Transparently write transactions in batch of 500 commands
  # If program is terminating, specifying {closing} appends the final :commit
  def updateTransaction(self):
    if self.cmdCounter > 0:
      self.write(";\n")
      
    self.cmdCounter += 1
  
  #
  # Format property key-value with account to Cypher syntax
  def formatProperty(self, k, v):
    if type(v) == str:
      return '%s: "%s"' % (k, self.sanitize(v))
    
    return '%s: %s' % (k, v)

  
  #
  # Convert properties held by a dictionary in a Cypher-compatible string
  def flattenProperties(self, props):
    return                                                                   \
      "" if props == None or not any(props)                                  \
      else "{" +                                                             \
        ", ".join([self.formatProperty(k, v) for (k, v) in props.items()]) + \
        "}"
  
  #
  # Convert properties held by a dictionary in a hash for identification
  def hashProperties(self, props):
    if props == None:
      raise ValueError('Cannot identify node stripped of properties')
    
    return hashlib.md5(self.flattenProperties(props).encode('utf-8')).hexdigest()
  
  #
  # Create a new node, given {label} and {properties}
  def node(self, label, properties = None, merge = False):
    self.updateTransaction()
    self.write(
      ('CREATE ' if not merge else 'MERGE ') +
      # Label
      "(:" + label +
      # Properties
      self.flattenProperties(properties) +
      # Closing parenthesis
      ")"
    )
  
  #
  # Ensure required matches for relationship are loaded
  def ensureMatch(self, key):
    # {nodeLbl1}:{nodeId1}:{nodeLbl2}:{nodeId2}
    keySplit = key.split(':')
    newMatches =                        \
      [                                 \
        ( keySplit[0], keySplit[1] ),   \
        ( keySplit[2], keySplit[3] )    \
      ]
    
    # If match is not yet loaded, make it so
    for newMatch in newMatches:
      # {nodeLbl}{nodeId}
      varName = newMatch[0] + newMatch[1]
      
      cmd =                                         \
        "MATCH (" + varName + ":" + newMatch[0] +   \
        self.rsProps[newMatch[1]] + ")\n"
      
      self.write(cmd)
    
  #
  # Write all pending relationship in a somewhat orderly fashion
  def flushRelationships(self):
    # (Legacy code)
    oDict = OrderedDict(sorted(self.rsDict.items(), key = lambda t: t[0]))
    
    for rsKey in oDict:
      
      while any(self.rsDict[rsKey]):
        self.updateTransaction()
        
        self.ensureMatch(rsKey)
        
        # Create actual rs
        self.write(self.rsDict[rsKey].pop())
  
  #
  # Create a new relationship between nodes
  def relationship(self,
                   nodeLbl1, nodeProps1,
                   nodeLbl2, nodeProps2,
                   rsName, rsProps = None):
    nodeHash1 = self.hashProperties(nodeProps1)
    nodeHash2 = self.hashProperties(nodeProps2)
    
    # {nodeLbl1}:{nodeHash1}:{nodeLbl2}:{nodeHash2}
    key =                 \
      nodeLbl1 + ":" +    \
      nodeHash1 + ":" +   \
      nodeLbl2 + ":" +    \
      nodeHash2
    
    if not key in self.rsDict:
      self.rsDict[key] = []
    
    # Prepare cypher command
    # ({nodeLbl1}{nodeId1})-[:{rsName}{props}]->({nodeLbl2}{nodeId2})
    cmd =                                                                       \
      "CREATE "                                                                 \
      "(" + nodeLbl1 + nodeHash1 + ")" +                                        \
      "-[:" + rsName + self.flattenProperties(rsProps) + "]->" + \
      "(" + nodeLbl2 + nodeHash2 + ")"
    
    # Append command to be written prior to termination
    # See `CypherWriter.flushRelationships`
    self.rsDict[key].append(cmd)
    
    # Alongside associated properties to MATCH the nodes
    self.rsProps[nodeHash1] = self.flattenProperties(nodeProps1)
    self.rsProps[nodeHash2] = self.flattenProperties(nodeProps2)
  
  #
  # Flush pending relationships, appends final :commit, close file
  def close(self):
    self.flushRelationships()
    self.updateTransaction()
    self.file.close()