// Ambient declarations for Cytoscape plugins that ship without types.
// We treat them as runtime-registered factories — TS just needs to know
// they exist and that registering them is a side effect on cytoscape.
declare module "cytoscape-cose-bilkent" {
  const ext: cytoscape.Ext;
  export default ext;
}

declare module "cytoscape-expand-collapse" {
  const ext: cytoscape.Ext;
  export default ext;
}
