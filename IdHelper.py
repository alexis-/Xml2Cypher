#!/usr/bin/env python

class IdHelper:
  idDict = {}
  
  def new(self, label):
    if not label in self.idDict:
      self.idDict[label] = 0
    
    newId = self.idDict[label] + 1
    self.idDict[label] = newId
    
    return newId