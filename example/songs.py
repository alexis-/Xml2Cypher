#!/usr/bin/env python

# Xml : dictionary mapping
import xmltodict
# X2C
import CypherWriter
import Xml2Cypher

def parseTags(params):
  return params['tags'].split(' ')

def main():
  x2c = Xml2Cypher.parse('songs.schema')
  
  nodeWriter = CypherWriter.CypherWriter('songs-nodes.cql')
  rsWriter = CypherWriter.CypherWriter('songs-relationships.cql')
  
  # CAPEC XML definitions
  capecXMLFile = 'songs.xml'
  capecXMLEncoding = 'utf8'

  # Load XML file into a dictionary object
  with open(capecXMLFile, encoding=capecXMLEncoding) as fd:
    root = xmltodict.parse(fd.read())
    
    x2c.apply(root, nodeWriter, rsWriter, { 'parseTags': parseTags })
  
  nodeWriter.close()
  rsWriter.close()

main()