# Sample corpus

Meridian Transit Authority is invented. So is every document in this folder,
every person named in them and every number they contain. They exist to give the
graph something concrete to be wrong about, and to let the eval cases assert on
fixed chunk ids.

The corpus is deliberately uneven: some claims a diagnostic would want are
simply not in here. A retriever that cannot find a data owner should produce a
finding with no evidence, and that finding should fail the groundedness floor.
An eval suite where the evidence is always available proves nothing.
