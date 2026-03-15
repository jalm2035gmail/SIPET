  function updateBackgroundPreview(color) {
    var preview = el('ped-bg-preview');
    if (!preview) return;
    preview.style.background = color || '#3f6f12';
  }
  function applyPalette(kind) {
    var paletteMap = {
      'creation-1': ['#e89a6d', '#65a620', '#3f6f12'],
      'creation-2': ['#65a620', '#e89a6d', '#ffffff'],
      'creation-3': ['#3f6f12', '#c79f66', '#ffffff'],
      'combo-1': ['#e8e95d', '#63b28e', '#16647d'],
      'combo-2': ['#ecdbac', '#e39b6e', '#bf4343'],
      'combo-3': ['#eed27b', '#6eb1d8', '#1d5f96'],
      'combo-4': ['#ece76e', '#edc84f', '#5462f0'],
      'combo-5': ['#dbe870', '#ebefef', '#0f1d59'],
      'combo-6': ['#bbe885', '#d57183', '#8e1010'],
      'brand-kit': ['#e89a6d', '#3f6f12', '#ffffff']
    };
    if (kind === 'brand-add') {
      toast('Pendiente conectar colores personalizados de la marca.');
      return;
    }
    var palette = paletteMap[kind];
    if (!palette || !editor) return;
    var selected = editor.getSelected && editor.getSelected();
    if (selected && selected.addStyle) {
      selected.addStyle({
        color: palette[2] || '#111827',
        background: palette[0],
        borderColor: palette[1] || palette[0]
      });
      toast('Paleta aplicada al elemento seleccionado.');
      return;
    }
    var slide = currentSlide();
    if (slide) {
      slide.bg_color = palette[1] || palette[0];
      if (inputSlideBgColor) inputSlideBgColor.value = slide.bg_color;
      loadSlideIntoEditor(slide);
      toast('Paleta aplicada a la diapositiva.');
    }
  }
  function setBackgroundPanelVisible(show) {
    if (!backgroundPanel) return;
    backgroundPanel.classList.toggle('is-active', !!show);
    if (show) {
      setSidepanelMode('background');
      var slide = currentSlide();
      updateBackgroundPreview((slide && slide.bg_color) || '#3f6f12');
      return;
    }
    setSidepanelMode('default');
  }
  function setPagesPanelVisible(show) {
    if (!pagesPanel) return;
    pagesPanel.classList.toggle('is-active', !!show);
    if (show) {
      setSidepanelMode('pages');
      return;
    }
    setSidepanelMode('default');
  }
  function applyBackgroundColor(color, applyAll) {
    if (color === 'custom' || color === 'palette') {
      if (inputSlideBgColor) inputSlideBgColor.click();
      return;
    }
    if (!color) return;

    if (applyAll) {
      slides.forEach(function (slide) {
        slide.bg_color = color;
      });
      if (inputSlideBgColor) inputSlideBgColor.value = color;
      renderSlideList();

      var activeAll = currentSlide();
      if (activeAll) {
        paintEditorBackground(activeAll);
      }

      updateBackgroundPreview(color);
      toast('Fondo aplicado a todas las páginas.');
      return;
    }

    var slide = currentSlide();
    if (!slide) return;

    slide.bg_color = color;
    if (inputSlideBgColor) inputSlideBgColor.value = color;

    paintEditorBackground(slide);
    renderSlideList();
    updateBackgroundPreview(color);
    toast('Fondo aplicado a la diapositiva.');
  }

