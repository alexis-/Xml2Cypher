MATCH (Artist28c7f06b05f12aacda482ab8357af7ba:Artist{id: 1})
MATCH (Song28c7f06b05f12aacda482ab8357af7ba:Song{id: 1})
CREATE (Artist28c7f06b05f12aacda482ab8357af7ba)-[:AUTHORED]->(Song28c7f06b05f12aacda482ab8357af7ba);
MATCH (Artist3332d01a379d5992acce8aaaba841f5f:Artist{id: 2})
MATCH (Song3332d01a379d5992acce8aaaba841f5f:Song{id: 2})
CREATE (Artist3332d01a379d5992acce8aaaba841f5f)-[:AUTHORED]->(Song3332d01a379d5992acce8aaaba841f5f);
MATCH (Artistae7ad2ed01e8f053157d7c0f7c9406c0:Artist{id: 3})
MATCH (Songae7ad2ed01e8f053157d7c0f7c9406c0:Song{id: 3})
CREATE (Artistae7ad2ed01e8f053157d7c0f7c9406c0)-[:AUTHORED]->(Songae7ad2ed01e8f053157d7c0f7c9406c0);
MATCH (Song28c7f06b05f12aacda482ab8357af7ba:Song{id: 1})
MATCH (Tag28c7f06b05f12aacda482ab8357af7ba:Tag{id: 1})
CREATE (Song28c7f06b05f12aacda482ab8357af7ba)-[:HAS_TAG]->(Tag28c7f06b05f12aacda482ab8357af7ba);
MATCH (Song28c7f06b05f12aacda482ab8357af7ba:Song{id: 1})
MATCH (Tag3332d01a379d5992acce8aaaba841f5f:Tag{id: 2})
CREATE (Song28c7f06b05f12aacda482ab8357af7ba)-[:HAS_TAG]->(Tag3332d01a379d5992acce8aaaba841f5f);
MATCH (Song3332d01a379d5992acce8aaaba841f5f:Song{id: 2})
MATCH (Tagae7ad2ed01e8f053157d7c0f7c9406c0:Tag{id: 3})
CREATE (Song3332d01a379d5992acce8aaaba841f5f)-[:HAS_TAG]->(Tagae7ad2ed01e8f053157d7c0f7c9406c0);
MATCH (Song3332d01a379d5992acce8aaaba841f5f:Song{id: 2})
MATCH (Tagff155f4d405374cdc37d0b62075d5f84:Tag{id: 4})
CREATE (Song3332d01a379d5992acce8aaaba841f5f)-[:HAS_TAG]->(Tagff155f4d405374cdc37d0b62075d5f84);
MATCH (Songae7ad2ed01e8f053157d7c0f7c9406c0:Song{id: 3})
MATCH (Tag449ffda81f46f6bd60f4eebb0947797f:Tag{id: 5})
CREATE (Songae7ad2ed01e8f053157d7c0f7c9406c0)-[:HAS_TAG]->(Tag449ffda81f46f6bd60f4eebb0947797f);
MATCH (Songae7ad2ed01e8f053157d7c0f7c9406c0:Song{id: 3})
MATCH (Tagceb829ebcf7c094e3c8aec8092ec2b3d:Tag{id: 6})
CREATE (Songae7ad2ed01e8f053157d7c0f7c9406c0)-[:HAS_TAG]->(Tagceb829ebcf7c094e3c8aec8092ec2b3d);
