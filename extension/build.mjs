import esbuild from "esbuild";

const watch = process.argv.includes("--watch");

/** Build minimal : deux bundles, aucune dépendance runtime. */
const options = {
  entryPoints: ["src/sidepanel.ts", "src/background.ts"],
  bundle: true,
  outdir: "dist",
  format: "esm",
  target: "chrome116",
  minify: false,
  sourcemap: false,
  logLevel: "info",
};

if (watch) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  console.log("watch mode actif");
} else {
  await esbuild.build(options);
}
