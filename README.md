# smi2ass

`smi2ass` is a command-line tool that converts SAMI to SSA/ASS (SubStation Alpha).

[Download the executable](https://github.com/LinearAlpha/smi2ass/releases) and run it with `.smi` file paths:

```
$ smi2ass my_subtitles.smi
```

`smi2ass` will convert the specified `.smi` files into `.ass` files. It will also generate multiple `.ass` files
if the `.smi` file contains the subtitles of multiple languages.

```
$ ls my_subtitles.*
my_subtitles.eng.ass
my_subtitles.kor.ass
```

## Supported tags

`smi2ass` supports `<p>`, `<br>`, `<b>`. `<i>`, `<u>`, `<s>`, `<font>` and `<rt>` (Ruby tags).

## Fixing a bad SAMI file

`smi2ass` will output current file name working. If prints the problematic SAMI fragment if it failed the conversion,
so you can find the location of the problem in your `.smi` file, fix it and run again:

```
$ smi2ass my_bad_subtitles.smi
Failed to extract time code: <sync star=1234>
```

## Testing

Install the runtime dependencies and run the test suite:

```shell
python -m pip install beautifulsoup4 chardet webcolors
python -m unittest discover -s src/test -v
```

## Credits

The conversion script was initially forked from [service.subtitles.gomtv](https://github.com/hojel/service.subtitles.gomtv/tree/3a7342961e140eaf8250659b0ac6158ce5e6bc5c/resources/lib) and [smi2ass](https://github.com/trustin/smi2ass/tree/v0.1.1)

Since then, [@LinearAlpha](https://github.com/LinearAlpha) made the following changes:
- Fixed color conversion problem (RGB -> BGR)
- Rewrite code by using classes (OPP style)
- Updated Python from 3.6.X to 3.8.X
- Convert ASS setting into JSON file so user can easily modify if it needed
- Added a class called "AssStyle" so user can update font name, font size, title, and video resolution from the command line or simply calling setter method

Additional contributions:
- [@najoan125](https://github.com/najoan125) fixed named color conversion in `<font>` tags by removing the leading `#` before RGB-to-BGR conversion ([#1](https://github.com/LinearAlpha/smi2ass/pull/1)).
