-- Resolve local Markdown links against the source document directory before
-- Chromium prints the temporary HTML file. Web URLs and internal anchors stay
-- unchanged.

local source_dir = os.getenv("MD_PDF_SOURCE_DIR")

function Link(element)
  local target = element.target

  if not source_dir or target == "" or target:sub(1, 1) == "#" then
    return nil
  end

  if target:match("^[%a][%w+.-]*:") then
    return nil
  end

  local absolute
  if target:sub(1, 1) == "/" then
    absolute = pandoc.path.normalize(target)
  else
    absolute = pandoc.path.normalize(pandoc.path.join({source_dir, target}))
  end

  element.target = "file://" .. absolute
  return element
end
