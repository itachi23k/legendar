from pathlib import Path
from core.legend_renderer import LegendRenderer
from core.logo_inserter import LogoInserter

class FileProcessor:
    """Processa múltiplas imagens aplicando legenda e logo."""

    def __init__(self, renderer: LegendRenderer, logo_inserter: LogoInserter = None):
        self.renderer = renderer
        self.logo_inserter = logo_inserter

    def process_batch(self, image_paths, text, font_name,
                      output_folder=None, prefix="_legendado",
                      apply_logo=False):
        """Processa múltiplas imagens."""
        results = []
        for img_path in image_paths:
            path = Path(img_path)
            if not path.exists():
                continue

            if output_folder:
                out_dir = Path(output_folder)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{path.stem}{prefix}{path.suffix}"
            else:
                out_path = path.with_name(f"{path.stem}{prefix}{path.suffix}")

            if apply_logo and self.logo_inserter and self.logo_inserter.logo_exists():
                success = LogoInserter.composite_logo_and_legend(
                    str(path), str(out_path), self.logo_inserter,
                    self.renderer, text, font_name
                )
            else:
                success = self.renderer.render(str(path), str(out_path), text, font_name)

            if success:
                results.append(str(out_path))

        return results