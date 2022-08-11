import LtoP, PtoL, LtoL, PtoP

if __name__ == "__main__":
    print("\t-- Welcome to Youtube to Spotify Automater! --")
    print()
    print("[1] Convert all Youtube Liked Songs to a new Spotify Playlist")
    print("[2] Convert all Youtube Liked Songs to Spotify Liked Songs ")
    print("[3] Select a Youtube Playlist to convert to Spotify Liked Songs")
    print("[4] Select a Youtube Playlist to convert to a new Spotify Playlist")
    while True:
        try:
            playlist_num = int(input("Select Mode: "))
            if playlist_num > 4:
                print("Index out of range")
            else:
                break
        except ValueError:
            print("Enter integer value")

    if playlist_num == 1:
        LtoP.run()
    elif playlist_num == 2:
        LtoL.run()
    elif playlist_num == 3:
        PtoL.run()
    elif playlist_num == 4:
        PtoP.run()

    print("------------------------------------")
