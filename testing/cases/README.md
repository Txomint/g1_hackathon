# Case folders

One folder per expected action. The folder name is the label and must match an
action name exactly:

    STOP  FORWARD  BACKWARD  LEFT  RIGHT  ROTATE_LEFT  ROTATE_RIGHT  NONE
    ...plus any custom action name the recognizer under test can return.

Drop `.jpg` / `.png` frames into the folder matching what the recognizer
*should* say about them. Empty folders are ignored.

`NONE/` is for frames that should command nothing at all.
